"""03 Missingness, univariate EDA, ratings, prep time. Figures 1-12."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import CLEAN_CSV, RAW_CSV, save_json, save_table  # noqa: E402
from plot_style import COLORS, apply_style, savefig  # noqa: E402
from stats_utils import bootstrap_spearman_ci, pearson_with_n, spearman_with_n, summarize  # noqa: E402

apply_style()


def fig_missing_bar(raw: pd.DataFrame):
    cols = list(raw.columns)
    pct = raw.isna().mean() * 100
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    y = np.arange(len(cols))
    ax.barh(y, pct.values, color=COLORS["blue"], edgecolor="none")
    ax.set_yticks(y)
    ax.set_yticklabels(cols)
    ax.invert_yaxis()
    ax.set_xlabel("Missing values (%)")
    ax.set_title(f"Missing-value percentage by column (n = {len(raw):,} recipes)")
    for i, v in enumerate(pct.values):
        ax.text(v + 0.8, i, f"{v:.1f}%", va="center", fontsize=8, color=COLORS["gray"])
    ax.set_xlim(0, 110)
    savefig(fig, "fig01_missing_by_column")


def fig_missing_matrix(raw: pd.DataFrame):
    cols = ["Name", "Category", "Ingredients", "Nutrients", "Ratings", "Votes", "Prep_Time", "Cuisine"]
    mat = raw[cols].isna().to_numpy()
    # downsample rows for readability while preserving order blocks
    step = max(1, len(mat) // 900)
    shown = mat[::step]
    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    ax.imshow(shown.T, aspect="auto", cmap="Greys", interpolation="nearest", vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(cols)))
    ax.set_yticklabels(cols)
    ax.set_xlabel(f"Recipes (every {step}th row; black = missing)")
    ax.set_title("Missingness pattern across recipes")
    savefig(fig, "fig02_missingness_matrix")


def fig_ingredient_hist(df: pd.DataFrame):
    x = df.loc[df["in_frequency_corpus"], "unique_ingredient_count"].dropna().astype(float)
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    bins = np.arange(x.min() - 0.5, x.max() + 1.5, 1)
    ax.hist(x, bins=bins, color=COLORS["blue"], edgecolor="white", linewidth=0.4)
    ax.axvline(x.median(), color=COLORS["orange"], ls="--", label=f"median = {x.median():.0f}")
    ax.axvline(x.mean(), color=COLORS["red"], ls=":", label=f"mean = {x.mean():.2f}")
    ax.set_xlabel("Unique ingredients per recipe (count)")
    ax.set_ylabel("Number of recipes")
    ax.set_title(f"Distribution of unique ingredient count (n = {len(x):,})")
    ax.legend(frameon=False)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    savefig(fig, "fig03_ingredient_count_hist")
    return summarize(x)


def fig_ingredient_violin(df: pd.DataFrame):
    x = df.loc[df["in_frequency_corpus"], "unique_ingredient_count"].dropna().astype(float)
    fig, ax = plt.subplots(figsize=(5.4, 4.8))
    parts = ax.violinplot(x, showmeans=True, showmedians=True, widths=0.7)
    for pc in parts["bodies"]:
        pc.set_facecolor(COLORS["light"])
        pc.set_edgecolor(COLORS["blue"])
        pc.set_alpha(1)
    ax.boxplot(x, widths=0.18, showfliers=True, flierprops={"marker": ".", "markersize": 3, "alpha": 0.4})
    ax.set_xticks([1])
    ax.set_xticklabels(["Recipes"])
    ax.set_ylabel("Unique ingredients per recipe (count)")
    ax.set_title(f"Ingredient-count spread (n = {len(x):,})")
    savefig(fig, "fig04_ingredient_count_violin")


def fig_ingredient_ecdf(df: pd.DataFrame):
    x = np.sort(df.loc[df["in_frequency_corpus"], "unique_ingredient_count"].dropna().astype(float))
    y = np.arange(1, len(x) + 1) / len(x)
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.step(x, y, where="post", color=COLORS["blue"], lw=1.8)
    ax.set_xlabel("Unique ingredients per recipe (count)")
    ax.set_ylabel("Empirical CDF")
    ax.set_title(f"ECDF of recipe size (n = {len(x):,})")
    ax.set_ylim(0, 1.02)
    savefig(fig, "fig05_ingredient_count_ecdf")


def fig_categories(df: pd.DataFrame):
    cats = df.loc[df["in_frequency_corpus"] & df["Category"].notna(), "Category"]
    vc = cats.value_counts()
    top = vc.head(20)
    fig, ax = plt.subplots(figsize=(8.4, 6.2))
    y = np.arange(len(top))
    ax.barh(y, top.values, color=COLORS["blue"])
    ax.set_yticks(y)
    ax.set_yticklabels(top.index)
    ax.invert_yaxis()
    ax.set_xlabel("Number of recipes")
    ax.set_title(f"Top 20 categories among recipes with non-missing Category (n = {len(cats):,})")
    savefig(fig, "fig06_top_categories")
    cum = vc.cumsum() / vc.sum()
    return {
        "n_nonmissing": int(len(cats)),
        "n_unique": int(vc.size),
        "top20": {str(k): int(v) for k, v in top.items()},
        "top5_share": float(vc.head(5).sum() / vc.sum()),
        "top20_share": float(vc.head(20).sum() / vc.sum()),
        "n_to_50pct": int((cum < 0.5).sum() + 1),
        "coverage_of_all_recipes": float(len(cats) / df["in_frequency_corpus"].sum()),
    }


def fig_rating(df: pd.DataFrame):
    x = df.loc[df["in_frequency_corpus"], "rating_analyzed"].dropna().astype(float)
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.hist(x, bins=np.linspace(0, 5, 41), color=COLORS["blue"], edgecolor="white", linewidth=0.3)
    ax.axvline(x.mean(), color=COLORS["red"], ls="--", label=f"mean = {x.mean():.2f}")
    ax.axvline(x.median(), color=COLORS["orange"], ls=":", label=f"median = {x.median():.2f}")
    ax.set_xlabel("Rating (stars, 0–5 scale)")
    ax.set_ylabel("Number of recipes")
    ax.set_title(f"Rating distribution, excluding unrated zeros (n = {len(x):,})")
    ax.set_xlim(0, 5)
    ax.legend(frameon=False)
    savefig(fig, "fig07_rating_distribution")
    return summarize(x)


def fig_votes(df: pd.DataFrame):
    x = df.loc[df["in_frequency_corpus"], "votes_analyzed"].dropna().astype(float)
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))
    axes[0].hist(x, bins=40, color=COLORS["blue"], edgecolor="white", linewidth=0.3)
    axes[0].set_xlabel("Votes (count)")
    axes[0].set_ylabel("Number of recipes")
    axes[0].set_title("Linear scale")
    axes[1].hist(np.log1p(x), bins=40, color=COLORS["green"], edgecolor="white", linewidth=0.3)
    axes[1].set_xlabel("log1p(Votes)")
    axes[1].set_ylabel("Number of recipes")
    axes[1].set_title("log1p scale")
    fig.suptitle(f"Vote-count distribution (n = {len(x):,})", y=1.02)
    fig.tight_layout()
    savefig(fig, "fig08_votes_distribution")
    return summarize(x)


def fig_rating_vs_votes(df: pd.DataFrame):
    sub = df.loc[df["in_frequency_corpus"], ["rating_analyzed", "votes_analyzed", "log1p_votes"]].dropna()
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.scatter(sub["log1p_votes"], sub["rating_analyzed"], s=8, alpha=0.25, c=COLORS["blue"], linewidths=0)
    ax.set_xlabel("log1p(Votes)")
    ax.set_ylabel("Rating (stars)")
    ax.set_title(f"Rating versus popularity (n = {len(sub):,})")
    savefig(fig, "fig09_rating_vs_votes")
    few = sub[sub["votes_analyzed"] <= 3]
    many = sub[sub["votes_analyzed"] >= 50]
    return {
        "pearson": pearson_with_n(sub["log1p_votes"], sub["rating_analyzed"]),
        "spearman": spearman_with_n(sub["votes_analyzed"], sub["rating_analyzed"]),
        "spearman_ci": bootstrap_spearman_ci(sub["votes_analyzed"], sub["rating_analyzed"]),
        "low_vote_rating": summarize(few["rating_analyzed"]),
        "high_vote_rating": summarize(many["rating_analyzed"]),
        "n_votes_le_3": int(len(few)),
        "n_votes_ge_50": int(len(many)),
        "extreme_rating_share_low_votes": float(((few["rating_analyzed"] <= 2) | (few["rating_analyzed"] >= 4.9)).mean()) if len(few) else None,
        "extreme_rating_share_high_votes": float(((many["rating_analyzed"] <= 2) | (many["rating_analyzed"] >= 4.9)).mean()) if len(many) else None,
    }


def fig_prep(df: pd.DataFrame):
    x = df.loc[df["in_frequency_corpus"], "prep_time_minutes"].dropna().astype(float)
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))
    axes[0].hist(x, bins=40, color=COLORS["blue"], edgecolor="white", linewidth=0.3)
    axes[0].set_xlabel("Preparation time (minutes)")
    axes[0].set_ylabel("Number of recipes")
    axes[0].set_title("Raw scale")
    xpos = x[x > 0]
    axes[1].hist(np.log10(xpos), bins=30, color=COLORS["green"], edgecolor="white", linewidth=0.3)
    axes[1].set_xlabel("log10(preparation time in minutes)")
    axes[1].set_ylabel("Number of recipes")
    axes[1].set_title("Log10 scale (time > 0)")
    fig.suptitle(f"Preparation-time distribution (n = {len(x):,}; n>0 = {len(xpos):,})", y=1.02)
    fig.tight_layout()
    savefig(fig, "fig10_prep_time")
    return summarize(x)


def fig_prep_vs_size(df: pd.DataFrame):
    sub = df.loc[
        df["in_frequency_corpus"],
        ["prep_time_minutes", "unique_ingredient_count"],
    ].dropna()
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.scatter(sub["unique_ingredient_count"], sub["prep_time_minutes"], s=10, alpha=0.25, c=COLORS["blue"], linewidths=0)
    ax.set_xlabel("Unique ingredients per recipe (count)")
    ax.set_ylabel("Preparation time (minutes)")
    ax.set_title(f"Preparation time versus recipe size (n = {len(sub):,})")
    savefig(fig, "fig11_prep_vs_ingredient_count")
    return {
        "spearman": spearman_with_n(sub["unique_ingredient_count"], sub["prep_time_minutes"]),
        "spearman_ci": bootstrap_spearman_ci(sub["unique_ingredient_count"], sub["prep_time_minutes"]),
        "n": int(len(sub)),
    }


def fig_prep_vs_votes(df: pd.DataFrame):
    sub = df.loc[df["in_frequency_corpus"], ["prep_time_minutes", "votes_analyzed", "log1p_votes"]].dropna()
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.scatter(sub["prep_time_minutes"], sub["log1p_votes"], s=10, alpha=0.25, c=COLORS["blue"], linewidths=0)
    ax.set_xlabel("Preparation time (minutes)")
    ax.set_ylabel("log1p(Votes)")
    ax.set_title(f"Popularity versus preparation time (n = {len(sub):,})")
    savefig(fig, "fig12_prep_vs_votes")
    return {
        "spearman": spearman_with_n(sub["prep_time_minutes"], sub["votes_analyzed"]),
        "spearman_ci": bootstrap_spearman_ci(sub["prep_time_minutes"], sub["votes_analyzed"]),
        "n": int(len(sub)),
    }


def main():
    raw = pd.read_csv(RAW_CSV)
    df = pd.read_csv(CLEAN_CSV)
    fig_missing_bar(raw)
    fig_missing_matrix(raw)
    size_stats = fig_ingredient_hist(df)
    fig_ingredient_violin(df)
    fig_ingredient_ecdf(df)
    cat = fig_categories(df)
    cuisine = df.loc[df["in_frequency_corpus"] & df["Cuisine"].notna(), "Cuisine"]
    rating = fig_rating(df)
    votes = fig_votes(df)
    rv = fig_rating_vs_votes(df)
    prep = fig_prep(df)
    psize = fig_prep_vs_size(df)
    pvotes = fig_prep_vs_votes(df)

    payload = {
        "ingredient_count": size_stats,
        "category": cat,
        "cuisine": {
            "n_nonmissing": int(len(cuisine)),
            "pct": float(100 * len(cuisine) / df["in_frequency_corpus"].sum()),
            "n_unique": int(cuisine.nunique()),
            "counts": {str(k): int(v) for k, v in cuisine.value_counts().items()},
        },
        "rating": rating,
        "votes": votes,
        "rating_vs_votes": rv,
        "prep": prep,
        "prep_vs_size": psize,
        "prep_vs_votes": pvotes,
        "n_frequency_corpus": int(df["in_frequency_corpus"].sum()),
    }
    save_json("03_basic_eda.json", payload)
    save_table(pd.DataFrame([{"metric": k, **({} if not isinstance(v, dict) else v)} for k, v in [("size", size_stats), ("rating", rating), ("votes", votes), ("prep", prep)]]), "univariate_summaries.csv")
    print("basic eda complete")


if __name__ == "__main__":
    main()
