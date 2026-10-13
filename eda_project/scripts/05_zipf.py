"""05 Zipf analysis. Figure 16."""
from __future__ import annotations

import sys
from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import powerlaw
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import TABLES, save_json, save_table  # noqa: E402
from plot_style import COLORS, apply_style, savefig  # noqa: E402
from stats_utils import loglog_ols  # noqa: E402

apply_style()
warnings.filterwarnings("ignore", category=RuntimeWarning)


def fit_ranges(freq: pd.DataFrame) -> list[dict]:
    ranks = freq["rank"].to_numpy()
    f = freq["frequency"].to_numpy()
    rmax_all = int(ranks.max())
    ranges = []
    for rmin in [1, 5, 10, 20, 50]:
        for rmax in [100, 300, 1000, rmax_all]:
            if rmax <= rmin + 8:
                continue
            m = (ranks >= rmin) & (ranks <= rmax)
            fit = loglog_ols(ranks[m], f[m])
            fit.update({"rmin": rmin, "rmax": int(min(rmax, rmax_all)), "alpha_zipf": None if fit["slope"] is None else float(-fit["slope"])})
            ranges.append(fit)
    return ranges


def clauset_frequency_fit(frequencies: np.ndarray) -> dict:
    data = np.asarray(frequencies, dtype=float)
    data = data[np.isfinite(data) & (data > 0)]
    fit = powerlaw.Fit(data, discrete=True, verbose=False)
    xmin = float(fit.xmin)
    alpha = float(fit.alpha)
    tail = np.sort(data[data >= xmin])
    n = len(tail)
    # Continuous Pareto CDF approximation for GOF (powerlaw.KS is broken in this install)
    ccdf = np.power(tail / xmin, 1.0 - alpha)
    cdf_th = np.clip(1.0 - ccdf, 0, 1)
    cdf_emp = np.arange(1, n + 1) / n
    ks = float(np.max(np.abs(cdf_emp - cdf_th)))
    out = {
        "n": int(len(data)),
        "xmin": xmin,
        "alpha_freq_dist": alpha,
        "sigma": float(fit.sigma) if fit.sigma is not None else None,
        "ks": ks,
        "ks_method": "continuous_pareto_approximation_because_powerlaw.KS_is_broken",
        "n_in_tail": int(n),
    }
    comparisons = {}
    for alt in ["lognormal", "exponential"]:
        try:
            R, p = fit.distribution_compare("power_law", alt, normalized_ratio=True)
            comparisons[alt] = {"R": float(R), "p": float(p)}
        except Exception as e:
            comparisons[alt] = {"error": str(e)}
    out["comparisons"] = comparisons
    return out


def main():
    freq = pd.read_csv(TABLES / "ingredient_frequency_standard.csv")
    ranges = fit_ranges(freq)
    save_table(pd.DataFrame(ranges), "zipf_range_sensitivity.csv")

    # Primary descriptive fit: ranks 5 to 500 or available
    r = freq["rank"].to_numpy()
    f = freq["frequency"].to_numpy()
    primary_mask = (r >= 5) & (r <= min(500, r.max()))
    primary = loglog_ols(r[primary_mask], f[primary_mask])
    alpha = None if primary["slope"] is None else float(-primary["slope"])
    # MLE in log-space (Gaussian errors on log f): same as OLS
    clauset = clauset_frequency_fit(f)

    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    ax.scatter(r, f, s=9, alpha=0.35, c=COLORS["blue"], linewidths=0, label="empirical")
    if primary["slope"] is not None:
        rr = np.linspace(5, min(500, r.max()), 200)
        ff = np.exp(primary["intercept"] + primary["slope"] * np.log(rr))
        ax.plot(rr, ff, color=COLORS["orange"], lw=2, label=fr"OLS log-log, $r\in[5,500]$, $\alpha$={alpha:.2f}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Rank r")
    ax.set_ylabel("Frequency f(r) (recipes)")
    ax.set_title("Zipf analysis of cocktail ingredient usage")
    ax.legend(frameon=False, loc="upper right")
    savefig(fig, "fig16_zipf_fit")

    # Alternative distributions on rank-frequency residuals are not claimed as Clauset of ranks.
    payload = {
        "primary_range": {"rmin": 5, "rmax": int(min(500, r.max()))},
        "primary_ols": primary,
        "alpha_rank_frequency_ols": alpha,
        "alpha_note": (
            "alpha is the rank-frequency exponent in f(r) ~ r^{-alpha} from log-log OLS. "
            "Clauset MLE below is for the distribution of frequencies P(f)~f^{-alpha_freq}, a related but distinct quantity."
        ),
        "range_sensitivity": ranges,
        "clauset_on_frequencies": clauset,
        "n_ingredients": int(len(freq)),
        "linear_full_range_r2": loglog_ols(r, f).get("r2"),
        "full_range_alpha": None if loglog_ols(r, f).get("slope") is None else float(-loglog_ols(r, f)["slope"]),
    }
    save_json("05_zipf.json", payload)
    print("zipf complete", alpha, clauset.get("alpha_freq_dist"), clauset.get("xmin"))


if __name__ == "__main__":
    main()
