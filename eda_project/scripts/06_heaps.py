"""06 Heaps' law. Figures 17-18."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import INGREDIENTS_LONG, save_json, save_table  # noqa: E402
from plot_style import COLORS, apply_style, savefig  # noqa: E402
from stats_utils import loglog_ols  # noqa: E402

apply_style()

N_SHUFFLE = 100
SEED = 42


def vocab_sets(long_df: pd.DataFrame, level: str) -> list[set]:
    g = long_df[long_df[level].astype(str).str.len() > 0].groupby("row_id")[level].apply(lambda s: set(s.astype(str)))
    # preserve row_id order
    ids = sorted(g.index)
    return [g.loc[i] for i in ids]


def heaps_one(sets: list[set], order: np.ndarray) -> np.ndarray:
    seen: set = set()
    v = np.empty(len(order), dtype=np.int32)
    for i, idx in enumerate(order):
        seen |= sets[idx]
        v[i] = len(seen)
    return v


def fit_beta(v: np.ndarray, rmin: int = 20) -> dict:
    r = np.arange(1, len(v) + 1)
    m = r >= rmin
    return loglog_ols(r[m], v[m])


def main():
    long_df = pd.read_csv(INGREDIENTS_LONG)
    results = {}
    rng = np.random.default_rng(SEED)
    for level in ["standard", "moderate", "core"]:
        sets = vocab_sets(long_df, level)
        n = len(sets)
        curves = np.empty((N_SHUFFLE, n), dtype=np.int32)
        betas = []
        r2s = []
        for s in range(N_SHUFFLE):
            order = rng.permutation(n)
            v = heaps_one(sets, order)
            curves[s] = v
            fit = fit_beta(v)
            if fit["slope"] is not None:
                betas.append(fit["slope"])
                r2s.append(fit["r2"])
        mean_curve = curves.mean(axis=0)
        lo = np.percentile(curves, 2.5, axis=0)
        hi = np.percentile(curves, 97.5, axis=0)
        betas = np.asarray(betas)
        results[level] = {
            "n_recipes": n,
            "n_shuffle": N_SHUFFLE,
            "beta_mean": float(betas.mean()),
            "beta_std": float(betas.std(ddof=1)),
            "beta_ci95": [float(np.percentile(betas, 2.5)), float(np.percentile(betas, 97.5))],
            "r2_mean": float(np.mean(r2s)),
            "final_vocab_mean": float(mean_curve[-1]),
            "K_from_mean_curve": None,
        }
        r = np.arange(1, n + 1)
        mean_fit = fit_beta(mean_curve)
        results[level]["mean_curve_fit"] = mean_fit
        if mean_fit["intercept"] is not None:
            results[level]["K_from_mean_curve"] = float(np.exp(mean_fit["intercept"]))

        if level == "standard":
            fig, ax = plt.subplots(figsize=(7.0, 5.4))
            ax.fill_between(r, lo, hi, color=COLORS["light"], label="95% permutation band")
            ax.plot(r, mean_curve, color=COLORS["blue"], lw=1.8, label="mean V(R)")
            if mean_fit["slope"] is not None:
                pred = np.exp(mean_fit["intercept"] + mean_fit["slope"] * np.log(r))
                ax.plot(r, pred, color=COLORS["orange"], lw=1.6, ls="--", label=fr"fit $\beta$={mean_fit['slope']:.3f}")
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel("Number of recipes R")
            ax.set_ylabel("Unique ingredients V(R)")
            ax.set_title(f"Heaps' law in cocktail recipes ({N_SHUFFLE} shuffles)")
            ax.legend(frameon=False)
            savefig(fig, "fig17_heaps_curve")

            fig, ax = plt.subplots(figsize=(6.8, 4.4))
            ax.hist(betas, bins=18, color=COLORS["blue"], edgecolor="white")
            ax.axvline(betas.mean(), color=COLORS["orange"], ls="--", label=fr"mean $\beta$={betas.mean():.3f}")
            ax.set_xlabel("Heaps exponent β")
            ax.set_ylabel("Number of permutations")
            ax.set_title(fr"Permutation distribution of $\beta$ (n={N_SHUFFLE})")
            ax.legend(frameon=False)
            savefig(fig, "fig18_heaps_beta_hist")

            save_table(
                pd.DataFrame({"R": r, "V_mean": mean_curve, "V_lo": lo, "V_hi": hi}),
                "heaps_curve_standard.csv",
            )
            save_table(pd.DataFrame({"beta": betas}), "heaps_betas_standard.csv")

    save_json("06_heaps.json", results)
    print("heaps complete", results["standard"]["beta_mean"])


if __name__ == "__main__":
    main()
