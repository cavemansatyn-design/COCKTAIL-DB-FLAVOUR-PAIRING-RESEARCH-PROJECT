"""Project paths and JSON helpers."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGURES = ROOT / "figures"
TABLES = ROOT / "tables"
REPORT = ROOT / "report"
SCRIPTS = ROOT / "scripts"
RAW_CSV = DATA / "CocktailDB_raw.csv"
CLEAN_CSV = DATA / "CocktailDB_clean.csv"
INGREDIENTS_LONG = DATA / "ingredients_long.csv"
NUTRIENTS_WIDE = DATA / "nutrients_wide.csv"
RESULTS_DIR = TABLES / "json"

for p in (DATA, FIGURES, TABLES, REPORT, RESULTS_DIR):
    p.mkdir(parents=True, exist_ok=True)


def json_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        x = float(obj)
        if np.isnan(x) or np.isinf(x):
            return None
        return x
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(type(obj))


def save_json(name: str, payload) -> Path:
    path = RESULTS_DIR / name
    path.write_text(json.dumps(payload, indent=2, default=json_default), encoding="utf-8")
    return path


def load_json(name: str):
    path = RESULTS_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def save_table(df: pd.DataFrame, name: str) -> Path:
    path = TABLES / name
    df.to_csv(path, index=False)
    return path
