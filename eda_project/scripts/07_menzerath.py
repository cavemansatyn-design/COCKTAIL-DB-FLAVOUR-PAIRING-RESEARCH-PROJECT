"""07 Menzerath–Altmann analysis. Figure 19."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import CLEAN_CSV, INGREDIENTS_LONG, TABLES, save_json, save_table  # noqa: E402
from plot_style import COLORS, apply_style, savefig  # noqa: E402

apply_style()


def ma_fun(L, a, b, c):
    return a * np.power(L, b) * np.exp(c * L)


def fit_ma(L, y):
    L = np.asarray(L, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(L) & np.isfinite(y) & (L > 0) & (y > 0)
    L, y = L[m], y[m]
    if len(L) < 6:
        return None
    guesses = [(np.median(y), -0.2, -0.01), (np.median(y), 0.1, 0.0), (np.max(y), -0.3, 0.02)]
    best = None
    for p0 in guesses:
        try:
            popt, pcov = curve_fit(ma_fun, L, y, p0=p0, maxfev=20000)
        except Exception:
            continue
        pred = ma_fun(L, *popt)
        ss_res = np.sum((y - pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        se = np.sqrt(np.diag(pcov))
        cand = {
            "a": float(popt[0]),
            "b": float(popt[1]),
            "c": float(popt[2]),
            "se_a": float(se[0]),
            "se_b": float(se[1]),
            "se_c": float(se[2]),
            "r2": float(r2),
            "n_points": int(len(L)),
        }
        if best is None or cand["r2"] > best["r2"]:
            best = cand
            best["_popt"] = popt
    return best


def recipe_information(long_df: pd.DataFrame, freq: pd.DataFrame, level: str) -> pd.DataFrame:
    pmap = dict(zip(freq["ingredient"], freq["frequency"] / freq["frequency"].sum()))
    rows = []
    for rid, g in long_df.groupby("row_id"):
        ings = [x for x in g[level].astype(str).tolist() if x and x != "nan"]
        ings_u = list(dict.fromkeys(ings))
        L = len(ings_u)
        if L == 0:
            continue
        ss = []
        for ing in ings_u:
            p = pmap.get(ing)
            if p is None or p <= 0:
                continue
            ss.append(-np.log(p))
        if not ss:
            continue
        rows.append({"row_id": rid, "L": L, "y": float(np.mean(ss))})
    return pd.DataFrame(rows)


def main():
    long_df = pd.read_csv(INGREDIENTS_LONG)
    df = pd.read_csv(CLEAN_CSV)
    outputs = {}
    for level in ["standard", "moderate", "core"]:
        freq = pd.read_csv(TABLES / f"ingredient_frequency_{level}.csv")
        rec = recipe_information(long_df, freq, level)
        # binned by integer L
        grp = rec.groupby("L").agg(y_mean=("y", "mean"), y_std=("y", "std"), n=("y", "size")).reset_index()
        grp = grp[grp["n"] >= 5]
        fit_bins = fit_ma(grp["L"], grp["y_mean"])
        fit_raw = fit_ma(rec["L"], rec["y"])
        spearman = float(rec["L"].corr(rec["y"], method="spearman")) if len(rec) else None
        outputs[level] = {
            "n_recipes": int(len(rec)),
            "spearman_L_y": spearman,
            "fit_binned": {k: v for k, v in (fit_bins or {}).items() if k != "_popt"},
            "fit_raw": {k: v for k, v in (fit_raw or {}).items() if k != "_popt"},
            "L_summary": {
                "min": int(rec["L"].min()),
                "max": int(rec["L"].max()),
                "median": float(rec["L"].median()),
            },
        }
        if level == "standard":
            save_table(rec, "menzerath_recipe_points.csv")
            save_table(grp, "menzerath_binned.csv")
            fig, ax = plt.subplots(figsize=(7.2, 5.2))
            ax.scatter(rec["L"] + np.random.default_rng(0).uniform(-0.12, 0.12, len(rec)), rec["y"], s=8, alpha=0.15, c=COLORS["muted"], linewidths=0, label="recipes")
            ax.plot(grp["L"], grp["y_mean"], "o", color=COLORS["blue"], label="binned mean")
            ax.errorbar(grp["L"], grp["y_mean"], yerr=grp["y_std"] / np.sqrt(grp["n"].clip(lower=1)), fmt="none", ecolor=COLORS["blue"], alpha=0.7)
            for _, row in grp.iterrows():
                ax.text(row["L"], row["y_mean"], f" n={int(row['n'])}", fontsize=6, color=COLORS["gray"])
            if fit_bins and "_popt" in fit_bins:
                Ls = np.linspace(grp["L"].min(), grp["L"].max(), 200)
                ax.plot(Ls, ma_fun(Ls, *fit_bins["_popt"]), color=COLORS["orange"], lw=2, label="Menzerath–Altmann fit")
            ax.set_xlabel("Recipe size L (unique ingredients)")
            ax.set_ylabel("Average ingredient information y(L) = mean[−log p(i)]")
            ax.set_title(f"Menzerath–Altmann analysis of cocktail recipes (n = {len(rec):,})")
            ax.legend(frameon=False)
            savefig(fig, "fig19_menzerath")

    # alternative probability: p(i)=f_i/N_recipes rather than f_i/sum f
    freq = pd.read_csv(TABLES / "ingredient_frequency_standard.csv")
    n_rec = int(df["in_frequency_corpus"].sum())
    freq2 = freq.copy()
    freq2["frequency"] = freq2["frequency"]  # recipe_information uses frequency/sum; emulate alt by equalizing
    rec_alt = recipe_information(long_df, freq.assign(frequency=freq["frequency"] * 1.0), "standard")
    # recipe-level p(i)=fi/N
    pmap = dict(zip(freq["ingredient"], freq["frequency"] / n_rec))
    rows = []
    for rid, g in long_df.groupby("row_id"):
        ings_u = list(dict.fromkeys([x for x in g["standard"].astype(str).tolist() if x and x != "nan"]))
        L = len(ings_u)
        if L == 0:
            continue
        ss = [-np.log(pmap[i]) for i in ings_u if i in pmap and pmap[i] > 0]
        if ss:
            rows.append({"L": L, "y": float(np.mean(ss))})
    rec_pN = pd.DataFrame(rows)
    grp = rec_pN.groupby("L").agg(y_mean=("y", "mean"), n=("y", "size")).reset_index()
    grp = grp[grp["n"] >= 5]
    outputs["sensitivity_p_i_over_N_recipes"] = {
        "spearman": float(rec_pN["L"].corr(rec_pN["y"], method="spearman")),
        "fit_binned": {k: v for k, v in (fit_ma(grp["L"], grp["y_mean"]) or {}).items() if k != "_popt"},
    }
    save_json("07_menzerath.json", outputs)
    print("menzerath complete", outputs["standard"].get("spearman_L_y"), outputs["standard"].get("fit_binned"))


if __name__ == "__main__":
    main()
