"""08 Nutrition analysis. Figures 22-28."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parsers import NUTRIENT_UNITS  # noqa: E402
from paths import CLEAN_CSV, NUTRIENTS_WIDE, save_json, save_table  # noqa: E402
from plot_style import COLORS, apply_style, savefig  # noqa: E402
from stats_utils import summarize  # noqa: E402

apply_style()

CANDIDATES = {
    "lognorm": lambda x: stats.lognorm.fit(x, floc=0),
    "gamma": lambda x: stats.gamma.fit(x, floc=0),
    "weibull": lambda x: stats.weibull_min.fit(x, floc=0),
    "gaussian": lambda x: stats.norm.fit(x),
    "expon": lambda x: stats.expon.fit(x, floc=0),
}
DISTS = {
    "lognorm": stats.lognorm,
    "gamma": stats.gamma,
    "weibull": stats.weibull_min,
    "gaussian": stats.norm,
    "expon": stats.expon,
}


def ks_for(name, x):
    dist = DISTS[name]
    try:
        params = CANDIDATES[name](x)
        cdf = lambda v: dist.cdf(v, *params)
        D = stats.kstest(x, cdf).statistic
        return {"ks": float(D), "params": [float(p) for p in params]}
    except Exception as e:
        return {"ks": None, "error": str(e)}


def main():
    df = pd.read_csv(CLEAN_CSV)
    nut = pd.read_csv(NUTRIENTS_WIDE)
    n_all = len(df)
    cols = [c for c in NUTRIENT_UNITS if c in nut.columns]
    completeness = {}
    summaries = {}
    for c in cols:
        x = pd.to_numeric(nut[c], errors="coerce")
        n_obs = int(x.notna().sum())
        completeness[c] = {
            "n": n_obs,
            "pct_missing_all_recipes": float(100 * (1 - n_obs / n_all)),
            "pct_missing_among_nutrient_rows": float(100 * x.isna().mean()) if len(x) else 100,
            "unit": NUTRIENT_UNITS[c],
        }
        summaries[c] = {**summarize(x.dropna()), "unit": NUTRIENT_UNITS[c]}

    tbl = pd.DataFrame(
        [
            {
                "nutrient": c,
                "unit": NUTRIENT_UNITS[c],
                **summaries[c],
                "pct_missing_all_recipes": completeness[c]["pct_missing_all_recipes"],
            }
            for c in cols
        ]
    )
    save_table(tbl, "nutrient_descriptives.csv")

    # Fig 22 completeness among all recipes
    fig, ax = plt.subplots(figsize=(8.0, 5.4))
    names = cols
    avail = [100 - completeness[c]["pct_missing_all_recipes"] for c in names]
    y = np.arange(len(names))
    ax.barh(y, avail, color=COLORS["blue"])
    ax.set_yticks(y)
    ax.set_yticklabels([f"{c} ({NUTRIENT_UNITS[c]})" for c in names])
    ax.invert_yaxis()
    ax.set_xlabel("Recipes with extracted value (%)")
    ax.set_title(f"Nutrient field completeness (denominator = {n_all:,} recipes)")
    savefig(fig, "fig22_nutrient_completeness")

    cal = pd.to_numeric(df.get("calories"), errors="coerce")
    cal = cal[np.isfinite(cal)]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.hist(cal, bins=40, color=COLORS["blue"], edgecolor="white", linewidth=0.3)
    ax.set_xlabel("Calories (kcal; unit as reported, not verified per serving)")
    ax.set_ylabel("Number of recipes")
    ax.set_title(f"Calories distribution (n = {len(cal):,})")
    savefig(fig, "fig23_calories")

    macros = ["carbohydrates", "protein", "fat"]
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.6), sharey=False)
    for ax, m in zip(axes, macros):
        x = pd.to_numeric(df.get(m), errors="coerce")
        x = x[np.isfinite(x)]
        ax.hist(x, bins=30, color=COLORS["blue"], edgecolor="white", linewidth=0.3)
        ax.set_title(f"{m} (n={len(x):,})")
        ax.set_xlabel(f"{m} (g)")
    axes[0].set_ylabel("Recipes")
    fig.suptitle("Macronutrient distributions (observed values only)", y=1.03)
    fig.tight_layout()
    savefig(fig, "fig24_macros")

    corr_cols = [c for c in cols if pd.to_numeric(df[c], errors="coerce").notna().sum() >= 80]
    sub = df[corr_cols].apply(pd.to_numeric, errors="coerce")
    spear = sub.corr(method="spearman")
    save_table(spear.reset_index(), "nutrient_spearman.csv")
    fig, ax = plt.subplots(figsize=(8.4, 7.2))
    im = ax.imshow(spear.to_numpy(), cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr_cols)))
    ax.set_yticks(range(len(corr_cols)))
    ax.set_xticklabels(corr_cols, rotation=75, ha="right", fontsize=8)
    ax.set_yticklabels(corr_cols, fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, label="Spearman ρ")
    ax.set_title("Nutrient Spearman correlations (pairwise complete observations)")
    ax.grid(False)
    savefig(fig, "fig25_nutrient_corr")

    # log-normality for nutrients with enough positive values
    gof = {}
    plot_nuts = []
    for c in ["calories", "carbohydrates", "protein", "fat", "sugar", "sodium"]:
        if c not in df.columns:
            continue
        x = pd.to_numeric(df[c], errors="coerce")
        x = x[np.isfinite(x) & (x > 0)].to_numpy()
        if len(x) < 80:
            continue
        plot_nuts.append((c, x))
        lx = np.log(x)
        fits = {name: ks_for(name, x) for name in CANDIDATES}
        gof[c] = {
            "n_positive": int(len(x)),
            "n_zero": int((pd.to_numeric(df[c], errors="coerce") == 0).sum()),
            "log_skewness": float(stats.skew(lx, bias=False)),
            "log_mean": float(np.mean(lx)),
            "log_std": float(np.std(lx, ddof=1)),
            "fits": fits,
            "best": min((k for k in fits if fits[k]["ks"] is not None), key=lambda k: fits[k]["ks"]),
        }

    fig, axes = plt.subplots(2, 3, figsize=(10.4, 6.2))
    for ax, (c, x) in zip(axes.ravel(), plot_nuts + [(None, None)] * 6):
        if c is None:
            ax.axis("off")
            continue
        ax.hist(x, bins=30, color=COLORS["blue"], edgecolor="white", linewidth=0.3)
        ax.set_title(c)
        ax.set_xlabel(NUTRIENT_UNITS.get(c, ""))
    fig.suptitle("Original-scale nutrient distributions (positive values)")
    fig.tight_layout()
    savefig(fig, "fig26_nutrients_original")

    fig, axes = plt.subplots(2, 3, figsize=(10.4, 6.2))
    for ax, (c, x) in zip(axes.ravel(), plot_nuts + [(None, None)] * 6):
        if c is None:
            ax.axis("off")
            continue
        ax.hist(np.log(x), bins=30, color=COLORS["green"], edgecolor="white", linewidth=0.3)
        ax.set_title(f"ln({c})")
        ax.set_xlabel("natural log")
    fig.suptitle("Log-transformed nutrient distributions (strictly positive values)")
    fig.tight_layout()
    savefig(fig, "fig27_nutrients_log")

    labels = list(gof.keys())
    dist_names = list(CANDIDATES)
    ks_mat = np.array([[gof[c]["fits"][d]["ks"] if gof[c]["fits"][d]["ks"] is not None else np.nan for d in dist_names] for c in labels])
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    im = ax.imshow(ks_mat, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(dist_names)))
    ax.set_xticklabels(dist_names, rotation=30, ha="right")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    for i in range(ks_mat.shape[0]):
        for j in range(ks_mat.shape[1]):
            if np.isfinite(ks_mat[i, j]):
                ax.text(j, i, f" {ks_mat[i, j]:.3f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, label="KS distance D")
    ax.set_title("Goodness-of-fit (KS) for candidate nutrient distributions")
    ax.grid(False)
    savefig(fig, "fig28_distribution_gof")

    payload = {
        "n_recipes": n_all,
        "n_with_any_nutrient_string": int(df["Nutrients"].notna().sum()) if "Nutrients" in df.columns else None,
        "completeness": completeness,
        "summaries": summaries,
        "gof": gof,
        "carbs_alias": "Carbs and Carbohydrates were mapped to a single carbohydrates variable after verifying both are mass in grams in the observed strings.",
        "serving_caveat": "The dataset does not state that nutrient values are per serving; values are analyzed as reported.",
    }
    save_json("08_nutrition.json", payload)
    print("nutrition complete", {k: v["best"] for k, v in gof.items()})


if __name__ == "__main__":
    main()
