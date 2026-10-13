"""Run the full reproducible pipeline."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "01_data_audit.py",
    "02_cleaning.py",
    "03_basic_eda.py",
    "04_ingredient_analysis.py",
    "05_zipf.py",
    "06_heaps.py",
    "07_menzerath.py",
    "08_nutrition.py",
    "09_cooccurrence.py",
    "10_multivariate.py",
    "12_extended_additions.py",
    "11_generate_report.py",
]


def main():
    here = Path(__file__).resolve().parent
    for name in SCRIPTS:
        print("=" * 60)
        print("RUNNING", name)
        print("=" * 60)
        subprocess.check_call([sys.executable, str(here / name)], cwd=str(here))
    print("PIPELINE COMPLETE")


if __name__ == "__main__":
    main()
