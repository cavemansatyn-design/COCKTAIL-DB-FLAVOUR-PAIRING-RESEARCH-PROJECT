"""Shared statistical helpers."""
from __future__ import annotations

from typing import Optional

import numpy as np
from scipy import stats


def finite(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return x[np.isfinite(x)]


def summarize(x, ddof=1) -> dict:
    x = finite(x)
    n = len(x)
    if n == 0:
        return {"n": 0}
    q1, q3 = np.percentile(x, [25, 75])
    sk = float(stats.skew(x, bias=False)) if n > 2 else None
    return {
        "n": int(n),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "std": float(np.std(x, ddof=ddof)) if n > 1 else 0.0,
        "iqr": float(q3 - q1),
        "min": float(np.min(x)),
        "max": float(np.max(x)),
        "p10": float(np.percentile(x, 10)),
        "p90": float(np.percentile(x, 90)),
        "p95": float(np.percentile(x, 95)),
        "skewness": sk,
    }


def spearman_with_n(x, y) -> dict:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    n = int(m.sum())
    if n < 3:
        return {"n": n, "rho": None, "p": None}
    rho, p = stats.spearmanr(x[m], y[m])
    return {"n": n, "rho": float(rho), "p": float(p)}


def pearson_with_n(x, y) -> dict:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    n = int(m.sum())
    if n < 3:
        return {"n": n, "r": None, "p": None}
    r, p = stats.pearsonr(x[m], y[m])
    return {"n": n, "r": float(r), "p": float(p)}


def bootstrap_spearman_ci(x, y, n_boot=400, seed=1) -> dict:
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    n = len(x)
    if n < 10:
        return {"n": n, "ci95": None}
    rhos = []
    idx = np.arange(n)
    for _ in range(n_boot):
        b = rng.choice(idx, size=n, replace=True)
        rho, _ = stats.spearmanr(x[b], y[b])
        if np.isfinite(rho):
            rhos.append(rho)
    lo, hi = np.percentile(rhos, [2.5, 97.5])
    return {"n": n, "ci95": [float(lo), float(hi)]}


def loglog_ols(x, y) -> dict:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    if m.sum() < 3:
        return {"n": int(m.sum()), "slope": None, "intercept": None, "r2": None}
    lx, ly = np.log(x[m]), np.log(y[m])
    slope, intercept, r, p, se = stats.linregress(lx, ly)
    return {
        "n": int(m.sum()),
        "slope": float(slope),
        "intercept": float(intercept),
        "r": float(r),
        "r2": float(r**2),
        "p": float(p),
        "stderr": float(se),
    }
