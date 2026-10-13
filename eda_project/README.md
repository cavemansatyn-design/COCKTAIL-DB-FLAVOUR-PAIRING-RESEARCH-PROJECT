# CocktailDB exploratory analysis

Research-style EDA of `CocktailDB_raw.csv`, adapting (not copying) the statistical-law framework in Bagler et al., *Universal statistical laws governing culinary design* (arXiv:2604.28021v1).

## What this project does

- Audits data quality, duplicates, and missingness
- Builds a cleaned analytical table without modifying the original CSV
- Tests Zipf-like ingredient frequencies, Heaps’ law, and Menzerath–Altmann scaling
- Parses nutrients and compares candidate distributions
- Writes `report/CocktailDB_EDA_Research_Report.pdf`

The pipeline does **not** force the cocktail data to match the paper’s exponents.

## Layout

```
eda_project/
  data/          raw + cleaned tables
  figures/       PNG + PDF figures
  tables/        CSV summaries + tables/json results
  scripts/       numbered analysis scripts
  report/        final PDF
  README.md
```

## How to reproduce

From this directory:

```text
python scripts/run_all.py
```

Or run scripts 01–11 in order with the same Python interpreter.

Required packages (versions used in development): pandas, numpy, matplotlib, scipy, scikit-learn, networkx, powerlaw, reportlab.

## Outputs

- Frequency corpus: exact duplicate rows and extra Name+Ingredients clones are dropped; same-name variants with different ingredients are kept
- Main ingredient analyses use **standard** normalization (quantities/units stripped; lime vs lime juice preserved)
- Report numbers are read from `tables/json/*.json` rather than hard-coded

## Rating zeros

Every `Rating = 0` row has `Votes = 0`. Those rows are treated as **unrated** in `rating_analyzed` / `votes_analyzed`. Original columns remain in the cleaned file.
