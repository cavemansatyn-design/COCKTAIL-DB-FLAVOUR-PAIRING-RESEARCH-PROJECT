"""10 Multivariate EDA and optional PCA. Figures 29-30 plus extra panels."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import CLEAN_CSV, save_json, save_table  # noqa: E402
from plot_style import COLORS, apply_style, savefig  # noqa: E402
from stats_utils import bootstrap_spearman_ci, spearman_with_n  # noqa: E402

apply_style()

PAIRS = [
    ("unique_ingredient_count", "calories", "Ingredient count vs calories"),
    ("unique_ingredient_count", "sugar", "Ingredient count vs sugar"),
    ("unique_ingredient_count", "protein", "Ingredient count vs protein"),
    ("unique_ingredient_count", "rating_analyzed", "Ingredient count vs rating"),
    ("unique_ingredient_count", "votes_analyzed", "Ingredient count vs votes"),
    ("prep_time_minutes", "calories", "Prep time vs calories"),
    ("log1p_votes", "calories", "log1p(Votes) vs calories"),
]


def main():
    df = pd.read_csv(CLEAN_CSV)
    corpus = df[df["in_frequency_corpus"]].copy()
    pair_results = []
    fig, axes = plt.subplots(3, 3, figsize=(10.6, 9.2))
    axes = axes.ravel()
    for i, ax in enumerate(axes):
        if i >= len(PAIRS):
            ax.axis("off")
            continue
        a, b, title = PAIRS[i]
        sub = corpus[[a, b]].apply(pd.to_numeric, errors="coerce").dropna()
        xa, yb = sub[a].to_numpy(), sub[b].to_numpy()
        ax.scatter(xa, yb, s=8, alpha=0.25, c=COLORS["blue"], linewidths=0)
        sp = spearman_with_n(xa, yb)
        ci = bootstrap_spearman_ci(xa, yb)
        ax.set_xlabel(a)
        ax.set_ylabel(b)
        rho = sp.get("rho")
        ax.set_title(f"{title}\nn={sp['n']}, ρ={rho:.2f}" if rho is not None else title, fontsize=9)
        pair_results.append({"x": a, "y": b, **sp, **{"ci95": ci.get("ci95")}})
    fig.suptitle("Selected multivariate scatterplots (complete cases)", y=1.01)
    fig.tight_layout()
    savefig(fig, "fig_multivariate_pairs")

    save_table(pd.DataFrame(pair_results), "multivariate_spearman.csv")

    nut_cols = [c for c in ["calories", "fat", "carbohydrates", "protein", "sugar", "fiber", "sodium", "saturated_fat"] if c in corpus.columns]
    complete = corpus[nut_cols].apply(pd.to_numeric, errors="coerce").dropna()
    pca_out = {"n_complete": int(len(complete)), "n_variables": len(nut_cols), "variables": nut_cols}
    if len(complete) >= 50 and len(nut_cols) >= 3:
        Z = StandardScaler().fit_transform(complete.to_numpy())
        pca = PCA()
        scores = pca.fit_transform(Z)
        evr = pca.explained_variance_ratio_
        pca_out.update(
            {
                "explained_variance_ratio": [float(x) for x in evr],
                "cumulative": [float(x) for x in np.cumsum(evr)],
                "loadings_pc1": {k: float(v) for k, v in zip(nut_cols, pca.components_[0])},
                "loadings_pc2": {k: float(v) for k, v in zip(nut_cols, pca.components_[1])},
            }
        )
        fig, ax = plt.subplots(figsize=(7.0, 4.4))
        ax.bar(np.arange(1, len(evr) + 1), evr, color=COLORS["blue"])
        ax.plot(np.arange(1, len(evr) + 1), np.cumsum(evr), color=COLORS["orange"], marker="o", ms=4)
        ax.set_xlabel("Principal component")
        ax.set_ylabel("Explained variance ratio")
        ax.set_title(f"PCA of standardized nutrients (n = {len(complete):,} complete cases)")
        savefig(fig, "fig29_pca_variance")

        fig, ax = plt.subplots(figsize=(6.6, 5.6))
        ax.scatter(scores[:, 0], scores[:, 1], s=10, alpha=0.3, c=COLORS["blue"], linewidths=0)
        ax.set_xlabel(f"PC1 ({100*evr[0]:.1f}% var.)")
        ax.set_ylabel(f"PC2 ({100*evr[1]:.1f}% var.)")
        ax.set_title("PCA projection of recipes in nutrient space")
        savefig(fig, "fig30_pca_projection")
    else:
        pca_out["skipped"] = "Insufficient complete nutrient rows for PCA."

    strongest = sorted([p for p in pair_results if p.get("rho") is not None], key=lambda d: abs(d["rho"]), reverse=True)
    save_json("10_multivariate.json", {"pairs": pair_results, "pca": pca_out, "strongest": strongest[:8]})
    print("multivariate complete", pca_out.get("n_complete"))


if __name__ == "__main__":
    main()
