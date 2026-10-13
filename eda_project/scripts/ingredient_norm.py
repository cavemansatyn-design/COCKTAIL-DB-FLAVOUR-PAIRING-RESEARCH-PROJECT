"""Ingredient string normalization with an explicit hierarchy.

Levels
------
surface : lowercase, unicode/whitespace cleanup only
standard: also strip leading/trailing quantities and units
moderate: also strip garnish notes and common preparation descriptors
core    : sensitivity-only; maps ice variants together and drops 'fresh/freshly'

Semantic distinctions such as lime vs lime juice vs fresh lime juice are
preserved at surface/standard/moderate. Only the optional core level
removes 'fresh'.
"""
from __future__ import annotations

import re
import unicodedata

FRACTION_MAP = {
    "¼": "1/4",
    "½": "1/2",
    "¾": "3/4",
    "⅓": "1/3",
    "⅔": "2/3",
    "⅛": "1/8",
    "⅜": "3/8",
    "⅝": "5/8",
    "⅞": "7/8",
}

UNIT = (
    r"(?:fluid\s*ounces?|fl\.?\s*oz\.?|ounces?|oz\.?|"
    r"tablespoons?|tbsps?\.?|tbsp\.?|tblsp\.?|teaspoons?|tsps?\.?|tsp\.?|"
    r"cups?|pints?|quarts?|gallons?|"
    r"milliliters?|millilitres?|mls?\.?|ml\.?|liters?|litres?|"
    r"grams?|kilograms?|kg\.?|"
    r"pounds?|lbs?\.?|lb\.?|"
    r"jiggers?|dashes?|splash(?:es)?|drops?|pinche?s?|"
    r"parts?|measures?|shots?|ponies?|"
    r"bottles?|cans?|packages?|pkgs?\.?|envelopes?|"
    r"handfuls?|bunches?|cloves?)"
)
NUM = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d*\.\d+|\d+)"
QTY = rf"(?:{NUM}\s*[-–to]+\s*{NUM}|{NUM})"

LEAD_QTY = re.compile(rf"^(?:(?:a|an|one|two|three|four|five)\s+)?(?:{QTY}\s*(?:{UNIT})?\s+)+", re.I)
TRAIL_QTY = re.compile(rf"(?:\s+{QTY})?\s*{UNIT}\s*$", re.I)
OF_UNIT = re.compile(rf"^(?:a|an)\s+(?:dash|splash|pinch|drop|jigger|shot|part)\s+(?:of\s+)?", re.I)
PAREN = re.compile(r"\([^)]*\)")
GARNISH = re.compile(
    r"(?:,\s*)?(?:for garnish|to garnish|as garnish|garnish(?:es)?|as needed|or as needed|to taste|optional)\b",
    re.I,
)
PREP = re.compile(
    r"\b(?:freshly squeezed|freshly|thinly sliced|sliced into rounds|sliced|"
    r"diced|chopped|minced|grated|peeled|crushed|ground|canned|bottled|"
    r"thawed|frozen|room temperature|chilled|cooled|warmed|brewed|"
    r"juiced|zested|cut into pieces|cut into)\b",
    re.I,
)
MULTI_SPACE = re.compile(r"\s+")
PUNCT_EDGE = re.compile(r"^[\s,;:.\-/]+|[\s,;:.\-/]+$")

VARIANT_MAP = {
    "cointreau": "orange liqueur",
    "cointreau or other orange liqueur": "orange liqueur",
    "kahlua": "coffee liqueur",
    "kahlúa": "coffee liqueur",
    "coffee-flavored liqueur": "coffee liqueur",
    "coffee flavored liqueur": "coffee liqueur",
    "angostura bitters": "angostura bitters",
    "ice cubes": "ice cubes",
    "ice cube": "ice cubes",
}

ICE_CORE = re.compile(r"^(crushed ice|ice cubes|ice cube|ice)$")


def _basic_clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).strip().lower()
    for src, dst in FRACTION_MAP.items():
        text = text.replace(src, dst)
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = MULTI_SPACE.sub(" ", text)
    return text.strip(" ,;.")


def normalize_ingredient(text: str, level: str = "standard") -> str:
    s = _basic_clean(text)
    if not s:
        return ""
    if level == "surface":
        return s

    s = OF_UNIT.sub("", s)
    s = LEAD_QTY.sub("", s)
    s = TRAIL_QTY.sub("", s)
    s = MULTI_SPACE.sub(" ", s).strip(" ,;.")
    s = VARIANT_MAP.get(s, s)

    if level in {"moderate", "core"}:
        s = PAREN.sub(" ", s)
        s = GARNISH.sub(" ", s)
        s = PREP.sub(" ", s)
        s = s.replace(",", " ")
        s = MULTI_SPACE.sub(" ", s).strip(" ,;.")
        s = VARIANT_MAP.get(s, s)

    if level == "core":
        s = re.sub(r"\bfresh(?:ly)?\b", " ", s)
        s = MULTI_SPACE.sub(" ", s).strip()
        if ICE_CORE.match(s):
            s = "ice"
        s = VARIANT_MAP.get(s, s)

    s = PUNCT_EDGE.sub("", s)
    s = MULTI_SPACE.sub(" ", s).strip()
    return s


def split_ingredients(raw: str) -> list[str]:
    if raw is None or (isinstance(raw, float)):
        return []
    return [p.strip() for p in str(raw).split("|") if p.strip()]
