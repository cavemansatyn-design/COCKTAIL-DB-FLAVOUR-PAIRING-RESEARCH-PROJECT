"""04 Ingredient frequency. Figures 13-15."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import CLEAN_CSV, INGREDIENTS_LONG, save_json, save_table  # noqa: E402
from plot_style import COLORS, apply_style, savefig  # noqa: E402
from stats_utils import summarize  # noqa: E402

apply_style()


def recipe_frequencies(long_df: pd.DataFrame, level: str) -> pd.DataFrame:
    sub = long_df[long_df[level].astype(str).str.len() > 0]
    freq = sub.groupby(level)["row_id"].nunique().sort_values(ascending=False)
    out = freq.reset_index()
    out.columns = ["ingredient", "frequency"]
    out["rank"] = np.arange(1, len(out) + 1)
    out["p"] = out["frequency"] / sub["row_id"].nunique()
    return out


def main():
    long_df = pd.read_csv(INGREDIENTS_LONG)
    df = pd.read_csv(CLEAN_CSV)
    n_rec = int(df["in_frequency_corpus"].sum())
    freq = recipe_frequencies(long_df, "standard")
    save_table(freq, "ingredient_frequency_standard.csv")
    for lv in ["surface", "moderate", "core"]:
        save_table(recipe_frequencies(long_df, lv), f"ingredient_frequency_{lv}.csv")

    top = freq.head(30)
    fig, ax = plt.subplots(figsize=(8.6, 7.2))
    y = np.arange(len(top))
    ax.barh(y, top["frequency"], color=COLORS["blue"])
    ax.set_yticks(y)
    ax.set_yticklabels(top["ingredient"])
    ax.invert_yaxis()
    ax.set_xlabel("Number of distinct recipes containing the ingredient")
    ax.set_title(f"Top 30 ingredients by recipe frequency (n_recipes = {n_rec:,})")
    savefig(fig, "fig13_top30_ingredients")

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.hist(freq["frequency"], bins=40, color=COLORS["blue"], edgecolor="white", linewidth=0.3)
    ax.set_xlabel("Ingredient frequency (recipes)")
    ax.set_ylabel("Number of ingredients")
    ax.set_title(f"Distribution of ingredient frequencies (n_ingredients = {len(freq):,})")
    savefig(fig, "fig14_ingredient_frequency_hist")

    fig, ax = plt.subplots(figsize=(6.8, 5.4))
    ax.scatter(freq["rank"], freq["frequency"], s=8, alpha=0.35, c=COLORS["blue"], linewidths=0)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Rank r (log)")
    ax.set_ylabel("Frequency f(r) (recipes, log)")
    ax.set_title("Ingredient rank–frequency (log–log)")
    savefig(fig, "fig15_rank_frequency_loglog")

    repeats = int((long_df.groupby(["row_id", "standard"]).size() > 1).sum())
    payload = {
        "n_recipes": n_rec,
        "n_unique_standard": int(len(freq)),
        "top30": top.to_dict(orient="records"),
        "frequency_summary": summarize(freq["frequency"]),
        "share_top10": float(freq.head(10)["frequency"].sum() / freq["frequency"].sum()),
        "share_top1": float(freq.iloc[0]["frequency"] / n_rec),
        "hapax_n": int((freq["frequency"] == 1).sum()),
        "hapax_share_of_vocab": float((freq["frequency"] == 1).mean()),
        "within_recipe_repeated_pairs": repeats,
        "top_ingredient": str(freq.iloc[0]["ingredient"]),
        "top_frequency": int(freq.iloc[0]["frequency"]),
    }
    save_json("04_ingredients.json", payload)
    print("ingredient analysis complete", payload["n_unique_standard"])


if __name__ == "__main__":
    main()
