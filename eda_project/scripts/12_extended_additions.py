"""Minimal additions from recipes_extended_eda_report.pdf.

New analyses only:
- Prep-time boxplots by top-10 categories
- Bayesian vote-adjusted ratings (m=10)
- Zipf diagnostic: log-frequency boxplots by rank stratum
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import CLEAN_CSV, TABLES, save_json, save_table  # noqa: E402
from plot_style import COLORS, apply_style, savefig  # noqa: E402

apply_style()
M_PRIOR = 10.0


def main():
    df = pd.read_csv(CLEAN_CSV, low_memory=False)
    corp = df[df["in_frequency_corpus"]].copy()

    # --- Bayesian vote-adjusted rating (same formula as the extended notebook) ---
    sub = corp[["name", "rating_analyzed", "votes_analyzed"]].dropna()
    C = float(sub["rating_analyzed"].mean())
    v = sub["votes_analyzed"].to_numpy(dtype=float)
    r = sub["rating_analyzed"].to_numpy(dtype=float)
    adj = (v * r + M_PRIOR * C) / (v + M_PRIOR)
    sub = sub.assign(adj_rating=adj)
    top = sub.sort_values(["adj_rating", "votes_analyzed"], ascending=False).head(10)
    save_table(
        top.rename(columns={"name": "Name", "rating_analyzed": "Rating", "votes_analyzed": "Votes", "adj_rating": "Adj_Rating"}),
        "vote_adjusted_top10.csv",
    )

    # --- Prep time boxplot by top 10 categories ---
    both = corp[corp["Category"].notna() & corp["prep_time_minutes"].notna()].copy()
    cats = both["Category"].value_counts().head(10).index.tolist()
    box = both[both["Category"].isin(cats)].copy()
    p99 = float(np.nanpercentile(box["prep_time_minutes"], 99))
    groups = [box.loc[box["Category"] == c, "prep_time_minutes"].to_numpy(dtype=float) for c in cats]
    ns = [int(np.isfinite(g).sum()) for g in groups]
    meds = [float(np.nanmedian(g)) if len(g) else None for g in groups]

    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    bp = ax.boxplot(groups, tick_labels=cats, showfliers=True, patch_artist=True, flierprops={"marker": ".", "markersize": 4, "alpha": 0.45})
    for patch in bp["boxes"]:
        patch.set_facecolor(COLORS["light"])
        patch.set_edgecolor(COLORS["blue"])
    for med in bp["medians"]:
        med.set_color(COLORS["orange"])
    ax.set_ylim(0, max(p99 * 1.15, 1))
    ax.set_ylabel("Preparation time (minutes)")
    ax.set_xlabel("Category (top 10 by recipe count; labelled subset)")
    ax.set_title(f"Prep time by category (y-axis capped near 99th percentile = {p99:.1f} min)")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    savefig(fig, "fig31_prep_time_by_category_boxplot")

    # --- Zipf: log-frequency by rank stratum (boxplot) ---
    freq = pd.read_csv(TABLES / "ingredient_frequency_standard.csv")
    bins = [0, 10, 50, 200, 1000, np.inf]
    labels = ["r 1–10", "r 11–50", "r 51–200", "r 201–1000", "r > 1000"]
    freq["stratum"] = pd.cut(freq["rank"], bins=bins, labels=labels)
    zgroups = [np.log10(freq.loc[freq["stratum"] == lab, "frequency"].to_numpy(dtype=float)) for lab in labels]
    zn = [int(len(g)) for g in zgroups]

    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    bp = ax.boxplot(zgroups, tick_labels=labels, showfliers=True, patch_artist=True, flierprops={"marker": ".", "markersize": 3, "alpha": 0.35})
    for patch in bp["boxes"]:
        patch.set_facecolor(COLORS["light"])
        patch.set_edgecolor(COLORS["blue"])
    for med in bp["medians"]:
        med.set_color(COLORS["orange"])
    ax.set_ylabel("log10 ingredient frequency (recipes)")
    ax.set_xlabel("Ingredient rank stratum")
    ax.set_title("Zipf diagnostic: frequency spread by rank stratum")
    savefig(fig, "fig32_zipf_rank_stratum_boxplot")

    payload = {
        "bayes_m": M_PRIOR,
        "bayes_C": C,
        "bayes_n": int(len(sub)),
        "bayes_formula": "adj = (V*R + m*C) / (V + m)",
        "top10_adj": top.to_dict(orient="records"),
        "boxplot_categories": cats,
        "boxplot_n_per_category": dict(zip(cats, ns)),
        "boxplot_median_minutes": dict(zip(cats, meds)),
        "boxplot_p99": p99,
        "boxplot_n_total": int(len(box)),
        "zipf_stratum_n": dict(zip(labels, zn)),
        "zipf_stratum_median_log10f": {lab: float(np.median(g)) for lab, g in zip(labels, zgroups) if len(g)},
    }
    save_json("12_extended.json", payload)
    print("extended additions complete", payload["boxplot_n_total"], payload["bayes_n"])


if __name__ == "__main__":
    main()
