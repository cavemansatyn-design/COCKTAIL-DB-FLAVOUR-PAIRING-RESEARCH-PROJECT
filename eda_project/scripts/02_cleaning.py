"""02 Cleaning and analytical dataframe construction."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingredient_norm import normalize_ingredient, split_ingredients  # noqa: E402
from parsers import nutrients_to_frame, parse_prep_minutes, parse_votes  # noqa: E402
from paths import CLEAN_CSV, INGREDIENTS_LONG, NUTRIENTS_WIDE, RAW_CSV, save_json, save_table  # noqa: E402

LEVELS = ["surface", "standard", "moderate", "core"]


def _stats(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0}
    q1, q3 = np.percentile(x, [25, 75])
    return {
        "n": int(len(x)),
        "min": float(np.min(x)),
        "median": float(np.median(x)),
        "mean": float(np.mean(x)),
        "std": float(np.std(x, ddof=1)) if len(x) > 1 else 0.0,
        "iqr": float(q3 - q1),
        "p90": float(np.percentile(x, 90)),
        "p95": float(np.percentile(x, 95)),
        "max": float(np.max(x)),
    }


def main():
    raw = pd.read_csv(RAW_CSV)
    df = raw.copy()
    df["row_id"] = np.arange(len(df))
    df["name"] = df["Name"].astype(str)
    # Name.1 is redundant
    name_identical = bool(df["Name"].equals(df["Name.1"]))

    df["votes_raw"] = df["Votes"]
    df["votes"] = df["Votes"].map(parse_votes)
    malformed_votes = int(df["Votes"].notna().sum() - df["votes"].notna().sum())

    df["rating_raw"] = df["Ratings"]
    df["rating"] = df["Ratings"]
    unrated_mask = (df["rating"] == 0) & (df["votes"].fillna(-1) == 0)
    df["rating_unrated_zero"] = unrated_mask
    df["rating_analyzed"] = df["rating"].where(~unrated_mask)
    df["votes_analyzed"] = df["votes"].where(~unrated_mask)
    df["log1p_votes"] = np.log1p(df["votes_analyzed"])

    df["prep_time_raw"] = df["Prep_Time"]
    df["prep_time_minutes"] = df["Prep_Time"].map(parse_prep_minutes)

    exact_dup = df.duplicated(subset=[c for c in raw.columns], keep="first")
    name_ing_dup = df.duplicated(subset=["Name", "Ingredients"], keep="first")
    df["is_exact_duplicate"] = exact_dup
    df["is_name_ing_duplicate"] = name_ing_dup
    # Analytical corpus: drop exact row duplicates and Name+Ingredients duplicates.
    # Keep same-name recipes with different ingredient lists as variants.
    df["in_frequency_corpus"] = ~exact_dup & ~name_ing_dup

    long_rows = []
    count_rows = []
    corpus = df[df["in_frequency_corpus"]].copy()
    for _, row in corpus.iterrows():
        parts = split_ingredients(row["Ingredients"])
        norms = {lv: [normalize_ingredient(p, lv) for p in parts] for lv in LEVELS}
        raw_count = len(parts)
        rec = {
            "row_id": int(row["row_id"]),
            "name": row["name"],
            "raw_ingredient_count": raw_count,
        }
        for lv in LEVELS:
            cleaned = [x for x in norms[lv] if x]
            rec[f"unique_ingredient_count_{lv}"] = len(set(cleaned))
            rec[f"n_empty_after_{lv}"] = int(sum(1 for x in norms[lv] if not x))
            rec[f"n_within_recipe_repeat_{lv}"] = int(raw_count - len(set(cleaned))) if cleaned else 0
        count_rows.append(rec)
        for orig, std, mod, core, surf in zip(
            parts,
            norms["standard"],
            norms["moderate"],
            norms["core"],
            norms["surface"],
        ):
            long_rows.append(
                {
                    "row_id": int(row["row_id"]),
                    "name": row["name"],
                    "raw": orig,
                    "surface": surf,
                    "standard": std,
                    "moderate": mod,
                    "core": core,
                }
            )

    counts = pd.DataFrame(count_rows)
    df = df.merge(counts, on=["row_id", "name"], how="left")
    df["unique_ingredient_count"] = df["unique_ingredient_count_standard"]
    df["raw_ingredient_count"] = df["raw_ingredient_count"]

    long_df = pd.DataFrame(long_rows)
    long_df.to_csv(INGREDIENTS_LONG, index=False)

    nut = nutrients_to_frame(df["Nutrients"])
    nut = nut.reset_index()
    if "row_id" not in nut.columns:
        nut = nut.rename(columns={nut.columns[0]: "row_id"})
    nut.to_csv(NUTRIENTS_WIDE, index=False)
    df = df.merge(nut, on="row_id", how="left")

    # Drop redundant Name.1 from analytical table
    drop_cols = ["Name.1"]
    analytical = df.drop(columns=[c for c in drop_cols if c in df.columns])
    analytical.to_csv(CLEAN_CSV, index=False)

    vocab = {}
    for lv in LEVELS:
        v = long_df[lv].replace("", np.nan).dropna()
        vocab[lv] = {
            "n_mentions": int(len(v)),
            "n_unique": int(v.nunique()),
        }

    prep_vals = df.loc[df["in_frequency_corpus"], "prep_time_minutes"]
    payload = {
        "name_identical_to_name1": name_identical,
        "malformed_votes": malformed_votes,
        "n_unrated_zero_stars": int(unrated_mask.sum()),
        "decision_unrated_zeros": (
            "All Rating=0 rows co-occur with Votes=0. Treated as unrated "
            "(rating_analyzed/votes_analyzed set to missing) rather than genuine zero-star ratings."
        ),
        "n_exact_duplicate_dropped_for_frequency": int(exact_dup.sum()),
        "n_name_ing_duplicate_dropped_for_frequency": int((name_ing_dup & ~exact_dup).sum()),
        "n_frequency_corpus": int(df["in_frequency_corpus"].sum()),
        "n_same_name_variants_retained": "see audit: names with different ingredients kept",
        "prep_time_stats_minutes": _stats(prep_vals.to_numpy()),
        "prep_unparsed": int(df["Prep_Time"].notna().sum() - df["prep_time_minutes"].notna().sum()),
        "prep_zero": int((df["prep_time_minutes"] == 0).sum()),
        "prep_gt_1day": int((df["prep_time_minutes"] > 1440).sum()),
        "prep_gt_6h": int((df["prep_time_minutes"] > 360).sum()),
        "vocab_by_level": vocab,
        "dropped_redundant_columns": ["Name.1"],
        "normalization_hierarchy": {
            "surface": "lowercase and whitespace only",
            "standard": "surface + strip quantities/units (main analyses)",
            "moderate": "standard + garnish/prep descriptors",
            "core": "moderate + ice collapse + drop fresh (sensitivity only)",
        },
    }
    save_json("02_cleaning.json", payload)
    save_table(
        pd.DataFrame(
            [
                {"level": lv, "n_mentions": vocab[lv]["n_mentions"], "n_unique": vocab[lv]["n_unique"]}
                for lv in LEVELS
            ]
        ),
        "ingredient_vocab_by_normalization.csv",
    )
    print("cleaning complete", payload["n_frequency_corpus"], vocab)


if __name__ == "__main__":
    main()
