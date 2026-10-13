# Computational Flavour Pairing in Cocktails

A data-driven research project exploring cocktail ingredient compatibility by extending computational food-pairing methodologies to molecular-level flavour analysis. The project combines raw-data exploration, ingredient normalization, flavour-compound representations, co-occurrence analysis, graph-based modelling, and statistical benchmarking to investigate latent flavour associations and potential novel cocktail combinations.

**Repository:** [COCKTAIL-DB-FLAVOUR-PAIRING-RESEARCH-PROJECT](https://github.com/cavemansatyn-design/COCKTAIL-DB-FLAVOUR-PAIRING-RESEARCH-PROJECT)  
**Research:** Under Dr. Ganesh Bagler — [Google Scholar](https://scholar.google.co.in/citations?user=qyth_0QAAAAJ&hl=en)

## Research Questions

- How are ingredients distributed and combined across cocktail recipes?
- Can molecular flavour-compound representations help characterize ingredient-pair similarity?
- Which ingredient associations occur more often than expected under randomized baselines?
- Can network structure and statistical evidence help surface latent flavour associations and candidate cocktail combinations?

## Data Overview

### CocktailDB

The current exploratory analysis covers the following dataset scale:

| Measure | Count |
|---|---:|
| Raw CocktailDB records | 16,895 |
| Recipes retained for frequency analysis | 16,872 |
| Ingredient mentions | 79,411 |
| Normalized unique ingredients | 14,466 |
| Recipe categories | 429 |

The workflow examines raw records, ingredient mentions, recipe composition, category distributions, and normalized ingredient representations. Counts describe the analysed data and may change as cleaning and normalization rules evolve.

### Comparative culinary corpus

A separate culinary dataset used for comparative exploratory analysis contains:

| Measure | Count |
|---|---:|
| Recipes | 2,543 |
| Standardized ingredients | 194 |
| Categories | 15 |

These figures refer to a separate corpus and should not be interpreted as CocktailDB statistics.

## Methodology

### 1. Data preparation and exploratory analysis

- Inspect raw records and recipe structure.
- Normalize ingredient names and analyze ingredient-frequency distributions.
- Examine recipe sizes, category distributions, and ingredient usage patterns.
- Explore scaling relationships in culinary data.

### 2. Distributional analysis

The exploratory analysis investigates:

- **Zipf's law** — the relationship between ingredient frequency and rank.
- **Heaps' law** — how vocabulary size grows as more ingredient mentions are observed.
- **Menzerath–Altmann analysis** — relationships between the size of a construct and the size of its components.

The reported analysis includes **100 random permutations** and **400 bootstrap resamples** for distributional and uncertainty analysis.

### 3. Molecular flavour representations

Ingredient-level flavour-compound representations provide a basis for comparing ingredients through shared molecular flavour profiles. The research focuses on molecular similarity as a measurable signal; it does not assume that all compatible ingredients must share compounds or that similarity alone proves sensory compatibility.

### 4. Co-occurrence and graph-based modelling

Recipe ingredient combinations can be represented as co-occurrence relationships and ingredient networks. Graph-based analysis is used to investigate network structure and identify ingredient associations for further examination.

### 5. Null models and statistical inference

Observed pairing patterns can be compared with randomized controls to test whether an association exceeds what would be expected by chance. The broader methodological framework includes pairing statistics, differences from randomized expectations (\(\Delta N_s\)), standardized scores (Z-scores), ingredient-level contributions, and consideration of ingredient frequency and recipe-size effects.

Null-model comparisons and statistical significance should be interpreted in the context of the chosen randomization scheme and its assumptions. Molecular similarity, co-occurrence, and statistical significance are complementary signals rather than interchangeable measures.

## Workflow

1. Load and inspect raw cocktail records.
2. Clean and normalize recipe and ingredient data.
3. Produce descriptive statistics and ingredient-frequency analyses.
4. Examine distributional patterns and bootstrap/permutation results.
5. Map ingredients to flavour-compound representations where available.
6. Build ingredient-pair and co-occurrence representations.
7. Compare observed patterns with suitable randomized baselines.
8. Interpret statistically supported associations and investigate candidate pairings.

## Key Concepts

`CocktailDB` · `Computational Gastronomy` · `Flavour Compounds` · `Ingredient Normalization` · `Exploratory Data Analysis` · `Zipf's Law` · `Heaps' Law` · `Menzerath–Altmann Law` · `Co-occurrence Networks` · `Graph-based Modelling` · `Molecular Similarity` · `Permutation Testing` · `Bootstrap Resampling` · `Null Models` · `Z-scores` · `Statistical Inference`

## Research Scope and Limitations

- Dataset counts depend on the current extraction, cleaning, and normalization pipeline.
- Ingredient co-occurrence indicates a recipe-level association, not necessarily a sensory preference or causal relationship.
- Molecular overlap is one computational representation of flavour and does not fully capture concentration, preparation, aroma perception, or human preference.
- Randomized baselines must preserve the relevant data constraints to support meaningful comparisons.
- Candidate combinations generated computationally require domain interpretation and, where possible, sensory validation.

## Citation and Attribution

This project extends data-driven food-pairing ideas to cocktail recipes and molecular flavour representations. For background on computational food pairing and related work, see [Dr. Ganesh Bagler's Google Scholar profile](https://scholar.google.co.in/citations?user=qyth_0QAAAAJ&hl=en).

## Author

**Satyam Singh**  
GitHub: [@cavemansatyn-design](https://github.com/cavemansatyn-design)
