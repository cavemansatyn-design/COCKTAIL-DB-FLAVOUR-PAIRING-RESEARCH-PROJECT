"""Parsers for votes, preparation time, and nutrients."""
from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd

NUTRIENT_CANON = {
    "calories": "calories",
    "calorie": "calories",
    "kcal": "calories",
    "fat": "fat",
    "total fat": "fat",
    "carbohydrates": "carbohydrates",
    "carbohydrate": "carbohydrates",
    "carbs": "carbohydrates",
    "carb": "carbohydrates",
    "protein": "protein",
    "saturated fat": "saturated_fat",
    "polyunsaturated fat": "polyunsaturated_fat",
    "monounsaturated fat": "monounsaturated_fat",
    "trans fat": "trans_fat",
    "sugar": "sugar",
    "sugars": "sugar",
    "fiber": "fiber",
    "fibre": "fiber",
    "dietary fiber": "fiber",
    "sodium": "sodium",
    "potassium": "potassium",
    "calcium": "calcium",
    "iron": "iron",
    "vitamin a": "vitamin_a",
    "vitamin c": "vitamin_c",
    "cholesterol": "cholesterol",
}

NUTRIENT_UNITS = {
    "calories": "kcal",
    "fat": "g",
    "carbohydrates": "g",
    "protein": "g",
    "saturated_fat": "g",
    "polyunsaturated_fat": "g",
    "monounsaturated_fat": "g",
    "trans_fat": "g",
    "sugar": "g",
    "fiber": "g",
    "sodium": "mg",
    "potassium": "mg",
    "calcium": "mg",
    "iron": "mg",
    "vitamin_a": "IU",
    "vitamin_c": "mg",
    "cholesterol": "mg",
}

COLON_RE = re.compile(
    r"^\s*([A-Za-z][A-Za-z\s]*)\s*:\s*([\d.,]+)\s*([A-Za-zµμ%]*)\s*$"
)
COMPACT_RE = re.compile(
    r"^\s*([\d.,]+)\s*(kcal|calories?|g|mg|iu)?\s+([A-Za-z][A-Za-z\s]*)\s*$",
    re.I,
)

TIME_TOKEN = re.compile(
    r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(seconds?|secs?|minutes?|mins?|min|hours?|hrs?|hr|days?|d)\b|"
    r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|minutes?|mins?|min|hours?|hrs?|hr|days?|d)\b",
    re.I,
)


def parse_votes(value) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return np.nan
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def _unit_to_minutes(n: float, unit: str) -> float:
    u = unit.lower()
    if u.startswith("sec"):
        return n / 60.0
    if u.startswith("min"):
        return n
    if u.startswith("hr"):
        return n * 60.0
    if u.startswith("d"):
        return n * 1440.0
    return n


def parse_prep_minutes(value) -> Optional[float]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    s = str(value).strip()
    if s == "":
        return np.nan
    # duplicated phrases: "3 minutes 3 minutes"
    s_norm = re.sub(r"\s+", " ", s.lower())
    tokens = TIME_TOKEN.findall(s)
    minutes = []
    seen_key = []
    if tokens:
        for a, b, u1, c, u2 in tokens:
            if a and b and u1:
                n = (float(a) + float(b)) / 2.0
                m = _unit_to_minutes(n, u1)
                key = (round(m, 4), u1.lower()[:3])
            else:
                m = _unit_to_minutes(float(c), u2)
                key = (round(m, 4), u2.lower()[:3])
            if key in seen_key:
                continue
            seen_key.append(key)
            minutes.append(m)
        # If the string is an exact duplication of the same duration, keep once.
        if len(minutes) >= 2 and abs(minutes[0] - minutes[1]) < 1e-9 and s_norm.count("minute") >= 2:
            # still could be "5 minutes 20 minutes"
            half = len(s_norm) // 2
            if s_norm[:half].strip() == s_norm[half:].strip() or s_norm.replace(" ", "")[: len(s_norm.replace(" ", "")) // 2] * 2 == s_norm.replace(" ", ""):
                return minutes[0]
        return float(sum(minutes))
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return float(s)
    return np.nan


def _canon_label(label: str) -> Optional[str]:
    key = re.sub(r"\s+", " ", label.strip().lower())
    key = key.replace("total ", "")
    return NUTRIENT_CANON.get(key)


def parse_nutrient_string(text) -> dict:
    out = {}
    units = {}
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return out
    s = str(text).strip()
    if not s:
        return out
    for part in s.split("|"):
        part = part.strip()
        if not part:
            continue
        name = None
        val = None
        unit = ""
        m = COLON_RE.match(part)
        if m:
            name, val, unit = m.group(1), m.group(2), m.group(3)
        else:
            m = COMPACT_RE.match(part)
            if m:
                val, unit, name = m.group(1), m.group(2) or "", m.group(3)
            else:
                # "184 Calories"
                m2 = re.match(r"^\s*([\d.,]+)\s*(calories?|kcal)\s*$", part, re.I)
                if m2:
                    val, name, unit = m2.group(1), "calories", m2.group(2)
        if name is None or val is None:
            continue
        canon = _canon_label(name)
        if canon is None:
            continue
        try:
            num = float(str(val).replace(",", ""))
        except ValueError:
            continue
        out[canon] = num
        units[canon] = unit.lower()
    if units:
        out["_units"] = units
    return out


def nutrients_to_frame(series: pd.Series) -> pd.DataFrame:
    rows = []
    for i, val in series.items():
        parsed = parse_nutrient_string(val)
        parsed.pop("_units", None)
        parsed["row_id"] = i
        rows.append(parsed)
    wide = pd.DataFrame(rows).set_index("row_id")
    cols = [c for c in NUTRIENT_UNITS if c in wide.columns]
    return wide.reindex(columns=cols)
