"""01 Dataset audit."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import RAW_CSV, save_json, save_table  # noqa: E402


def main():
    df = pd.read_csv(RAW_CSV)
    n, p = df.shape
    dtypes = {c: str(t) for c, t in df.dtypes.items()}
    missing = df.isna().sum().astype(int).to_dict()
    missing_pct = (df.isna().mean() * 100).round(4).to_dict()
    nunique = df.nunique(dropna=False).astype(int).to_dict()

    name_eq = bool(df["Name"].equals(df["Name.1"]))
    name_mismatch = int((df["Name"].fillna("__NA__") != df["Name.1"].fillna("__NA__")).sum())
    exact_dups = int(df.duplicated().sum())
    exact_dup_rows = int(df.duplicated(keep=False).sum())
    name_dups = int(df["Name"].duplicated().sum())
    name_ing_dups = int(df.duplicated(subset=["Name", "Ingredients"]).sum())

    g = df.groupby("Name", dropna=False).agg(n=("Ingredients", "size"), n_ing=("Ingredients", "nunique"))
    same_name_multi = int((g["n"] > 1).sum())
    same_name_diff_ing = int(((g["n"] > 1) & (g["n_ing"] > 1)).sum())
    same_name_same_ing = int(((g["n"] > 1) & (g["n_ing"] == 1)).sum())

    fields = ["Category", "Nutrients", "Ratings", "Votes", "Prep_Time", "Cuisine"]
    mask = df[fields].notna()
    combo = mask.astype(int).astype(str).agg("".join, axis=1)
    combo_counts = combo.value_counts().head(25)
    combo_table = pd.DataFrame(
        {
            "pattern": combo_counts.index,
            "n": combo_counts.values.astype(int),
            "pct": (combo_counts.values / n * 100).round(3),
        }
    )
    combo_table["Category"] = combo_table["pattern"].str[0].map({"1": "present", "0": "missing"})
    combo_table["Nutrients"] = combo_table["pattern"].str[1].map({"1": "present", "0": "missing"})
    combo_table["Ratings"] = combo_table["pattern"].str[2].map({"1": "present", "0": "missing"})
    combo_table["Votes"] = combo_table["pattern"].str[3].map({"1": "present", "0": "missing"})
    combo_table["Prep_Time"] = combo_table["pattern"].str[4].map({"1": "present", "0": "missing"})
    combo_table["Cuisine"] = combo_table["pattern"].str[5].map({"1": "present", "0": "missing"})
    save_table(combo_table, "missingness_combinations.csv")

    rat_present_votes_missing = int(((df["Ratings"].notna()) & (df["Votes"].isna())).sum())
    votes_present_rat_missing = int(((df["Votes"].notna()) & (df["Ratings"].isna())).sum())
    both_rv = int(((df["Votes"].notna()) & (df["Ratings"].notna())).sum())
    neither_rv = int(((df["Votes"].isna()) & (df["Ratings"].isna())).sum())
    rating0 = int((df["Ratings"] == 0).sum())
    rating0_votes0 = int(((df["Ratings"] == 0) & (df["Votes"].astype(str) == "0")).sum())

    cuisine_vc = df["Cuisine"].value_counts(dropna=False)
    cat_vc = df["Category"].value_counts(dropna=True)

    payload = {
        "n_rows": n,
        "n_cols": p,
        "columns": list(df.columns),
        "dtypes": dtypes,
        "missing": missing,
        "missing_pct": missing_pct,
        "nunique": nunique,
        "name_equals_name1": name_eq,
        "name_mismatch_rows": name_mismatch,
        "exact_duplicate_rows_beyond_first": exact_dups,
        "exact_duplicate_row_instances": exact_dup_rows,
        "duplicate_recipe_names_beyond_first": name_dups,
        "unique_names": int(df["Name"].nunique()),
        "duplicate_name_plus_ingredients_beyond_first": name_ing_dups,
        "names_with_multiple_rows": same_name_multi,
        "names_with_different_ingredients": same_name_diff_ing,
        "names_with_identical_ingredients_repeats": same_name_same_ing,
        "ratings_present_votes_missing": rat_present_votes_missing,
        "votes_present_ratings_missing": votes_present_rat_missing,
        "ratings_and_votes_both_present": both_rv,
        "ratings_and_votes_both_missing": neither_rv,
        "rating_zero_n": rating0,
        "rating_zero_and_votes_zero": rating0_votes0,
        "cuisine_n_nonmissing": int(df["Cuisine"].notna().sum()),
        "cuisine_n_unique_nonmissing": int(df["Cuisine"].nunique(dropna=True)),
        "cuisine_top": {str(k): int(v) for k, v in cuisine_vc.head(20).items()},
        "category_n_nonmissing": int(df["Category"].notna().sum()),
        "category_n_unique": int(df["Category"].nunique(dropna=True)),
        "category_top": {str(k): int(v) for k, v in cat_vc.head(20).items()},
        "nutrients_n_nonmissing": int(df["Nutrients"].notna().sum()),
        "prep_n_nonmissing": int(df["Prep_Time"].notna().sum()),
        "votes_with_comma": int(df["Votes"].dropna().astype(str).str.contains(",").sum()),
        "paper_mapping": {
            "recipe": "one row; Name identifies the recipe label",
            "ingredient_phrase": "Ingredients (pipe-delimited free text, not NER-structured)",
            "ingredient_identity": "derived by normalization of Ingredients",
            "frequency_fi": "number of distinct recipes containing normalized ingredient i",
            "recipe_size_L": "unique_ingredient_count after normalization",
            "cuisine": "Cuisine (97.7% missing; not usable for cuisine-level laws)",
            "cooking_technique": "ABSENT",
            "utensil": "ABSENT",
            "instruction_steps": "ABSENT",
            "geography": "ABSENT",
            "macronutrients": "Nutrients free text (partial; two formats)",
            "cook_time": "Prep_Time (partial, heterogeneous units)",
        },
        "reproducible_from_this_dataset": [
            "ingredient frequency and Zipf-like rank-frequency analysis",
            "Heaps vocabulary growth over recipes",
            "Menzerath-Altmann using ingredient information vs recipe size",
            "nutrient extraction and log-normality tests where n is sufficient",
            "recipe size (ingredient count) distributions",
            "ratings/votes/prep-time EDA on observed subsets",
        ],
        "not_reproducible": [
            "NER decomposition into quantity/unit/state/preprocessing",
            "cooking-technique Zipf/Heaps/Menzerath analyses",
            "utensil vocabularies",
            "26-cuisine and 75-country stratified scaling",
            "instruction-step complexity",
            "geographic maps",
            "paper generative model calibration as a reproduction of their simulations",
            "per-serving nutrient standardization as implemented in RecipeDB",
        ],
    }
    save_json("01_audit.json", payload)

    dtypes_tbl = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(t) for t in df.dtypes],
            "n_unique": [int(df[c].nunique(dropna=False)) for c in df.columns],
            "n_missing": [int(df[c].isna().sum()) for c in df.columns],
            "pct_missing": [float(df[c].isna().mean() * 100) for c in df.columns],
        }
    )
    save_table(dtypes_tbl, "column_audit.csv")
    print("audit complete", n, p)


if __name__ == "__main__":
    main()
