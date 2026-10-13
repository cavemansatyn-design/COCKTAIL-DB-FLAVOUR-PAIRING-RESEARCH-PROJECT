"""11 Generate the research-style PDF from saved numerical results."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from PIL import Image as PILImage
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import FIGURES, REPORT, RESULTS_DIR, ROOT, TABLES, load_json  # noqa: E402

NAVY = HexColor("#1F3A5F")
RULE = HexColor("#2C5F8A")
MUTED = HexColor("#555555")
LIGHT = HexColor("#F3F6F9")
OUT = REPORT / "CocktailDB_EDA_Research_Report.pdf"
OUT_ROOT = ROOT.parent / "CocktailDB_EDA_Research_Report.pdf"


def P(text, style):
    return Paragraph(str(text), style)


def fmt(x, nd=3):
    if x is None:
        return "n/a"
    try:
        if isinstance(x, int) or (isinstance(x, float) and abs(x - round(x)) < 1e-12 and abs(x) >= 10):
            return f"{int(round(x)):,}"
        return f"{float(x):,.{nd}f}"
    except Exception:
        return str(x)


def pval(p):
    if p is None:
        return "n/a"
    p = float(p)
    if p < 1e-4:
        return "< 0.0001"
    return f"{p:.4f}"


def styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("CoverTitle", fontName="Times-Bold", fontSize=18, leading=22, alignment=TA_CENTER, textColor=NAVY, spaceAfter=8))
    ss.add(ParagraphStyle("CoverSub", fontName="Times-Italic", fontSize=11, leading=14, alignment=TA_CENTER, textColor=MUTED, spaceAfter=6))
    ss.add(ParagraphStyle("CoverMeta", fontName="Times-Roman", fontSize=10, leading=13, alignment=TA_CENTER, textColor=black, spaceAfter=4))
    ss.add(ParagraphStyle("H1", fontName="Times-Bold", fontSize=13, leading=16, textColor=NAVY, spaceBefore=14, spaceAfter=6))
    ss.add(ParagraphStyle("H2", fontName="Times-Bold", fontSize=11.5, leading=14, textColor=RULE, spaceBefore=10, spaceAfter=4))
    ss.add(ParagraphStyle("H3", fontName="Times-Bold", fontSize=10.5, leading=13, textColor=black, spaceBefore=8, spaceAfter=3))
    ss.add(ParagraphStyle("Body", fontName="Times-Roman", fontSize=9.5, leading=12.4, alignment=TA_JUSTIFY, spaceAfter=6))
    ss.add(ParagraphStyle("Exec", fontName="Times-Roman", fontSize=9.5, leading=12.2, alignment=TA_JUSTIFY, spaceAfter=5))
    ss.add(ParagraphStyle("Caption", fontName="Times-Italic", fontSize=8.5, leading=11, alignment=TA_LEFT, textColor=MUTED, spaceAfter=2))
    ss.add(ParagraphStyle("FigHead", fontName="Times-Bold", fontSize=9, leading=11.5, textColor=NAVY, spaceBefore=3, spaceAfter=1))
    ss.add(ParagraphStyle("BulletBody", fontName="Times-Roman", fontSize=9.5, leading=12.2, leftIndent=8, spaceAfter=2))
    ss.add(ParagraphStyle("TOC", fontName="Times-Roman", fontSize=10, leading=14, spaceAfter=2))
    ss.add(ParagraphStyle("Footer", fontName="Times-Roman", fontSize=8, textColor=MUTED, alignment=TA_CENTER))
    ss.add(ParagraphStyle("TableCell", fontName="Times-Roman", fontSize=7.5, leading=9.5))
    ss.add(ParagraphStyle("TableHead", fontName="Times-Bold", fontSize=7.5, leading=9.5, textColor=white))
    ss.add(ParagraphStyle("AbstractH", fontName="Times-Bold", fontSize=11, leading=13, alignment=TA_CENTER, textColor=NAVY, spaceAfter=6))
    return ss


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(18 * mm, A4[1] - 12 * mm, A4[0] - 18 * mm, A4[1] - 12 * mm)
    canvas.setFont("Times-Italic", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, A4[1] - 10 * mm, "CocktailDB exploratory analysis  |  adapted from Bagler et al. culinary scaling framework")
    canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
    canvas.drawCentredString(A4[0] / 2, 7 * mm, f"{doc.page}")
    canvas.restoreState()


def add_fig(story, S, stem, title, shows, insight, matters, evidence, caveat, width=165 * mm):
    path = FIGURES / f"{stem}.png"
    if not path.exists():
        story.append(P(f"[Missing figure file: {stem}]", S["Caption"]))
        return
    pw, ph = PILImage.open(path).size
    aspect = ph / float(pw) if pw else 0.62
    height = width * aspect
    max_h = 118 * mm
    if height > max_h:
        height = max_h
        width = height / aspect
    img = Image(str(path), width=width, height=height)
    img.hAlign = "CENTER"
    block = [
        P(title, S["FigHead"]),
        img,
        P(f"<b>What this figure shows.</b> {shows}", S["Caption"]),
        P(f"<b>Key insight.</b> {insight}", S["Caption"]),
        P(f"<b>Why it matters.</b> {matters}", S["Caption"]),
        P(f"<b>Statistical evidence.</b> {evidence}", S["Caption"]),
        P(f"<b>Caveat.</b> {caveat}", S["Caption"]),
        Spacer(1, 6),
    ]
    story.append(KeepTogether(block))


def table(data, col_widths):
    sty = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, HexColor("#C5CED6")),
            ("BACKGROUND", (0, 1), (-1, -1), white),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT]),
        ]
    )
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(sty)
    return t


def wrap_cells(rows, S, header=True):
    out = []
    for i, row in enumerate(rows):
        st = S["TableHead"] if header and i == 0 else S["TableCell"]
        out.append([P(str(c), st) for c in row])
    return out


def main():
    S = styles()
    A = load_json("01_audit.json")
    C = load_json("02_cleaning.json")
    E = load_json("03_basic_eda.json")
    I = load_json("04_ingredients.json")
    Z = load_json("05_zipf.json")
    H = load_json("06_heaps.json")
    M = load_json("07_menzerath.json")
    N = load_json("08_nutrition.json")
    CO = load_json("09_cooccurrence.json")
    MV = load_json("10_multivariate.json")
    X = load_json("12_extended.json")

    n = A["n_rows"]
    n_corp = C["n_frequency_corpus"]
    n_names = A["unique_names"]
    alpha = Z.get("alpha_rank_frequency_ols")
    beta = H["standard"]["beta_mean"]
    beta_ci = H["standard"]["beta_ci95"]
    ma_sp = M["standard"]["spearman_L_y"]
    ma_fit = M["standard"].get("fit_binned") or {}
    rating_n = E["rating"].get("n")
    cat_n = E["category"]["n_nonmissing"]
    cuisine_n = E["cuisine"]["n_nonmissing"]
    hapax = I["hapax_share_of_vocab"]
    top_ing = I["top_ingredient"]
    top_f = I["top_frequency"]
    n_ing = I["n_unique_standard"]

    gof = N.get("gof", {})
    best_gof = {k: v.get("best") for k, v in gof.items()}
    best_gof_txt = "; ".join(f"{k}: {v}" for k, v in best_gof.items()) or "n/a"
    cal_gof = gof.get("calories", {})
    carb_gof = gof.get("carbohydrates", {})
    pretty = {
        "unique_ingredient_count": "ingredient count",
        "calories": "calories",
        "sugar": "sugar",
        "protein": "protein",
        "rating_analyzed": "rating",
        "votes_analyzed": "votes",
        "prep_time_minutes": "prep time",
        "log1p_votes": "log1p(votes)",
    }
    strongest = MV.get("strongest") or []
    strongest_txt = ", ".join(
        f"{pretty.get(p['x'], p['x'])} vs {pretty.get(p['y'], p['y'])} (ρ={p['rho']:.2f}, n={p['n']})"
        for p in strongest[:3]
    )
    comps = Z.get("clauset_on_frequencies", {}).get("comparisons") or {}
    lr_txt = "; ".join(
        f"{k}: R={v['R']:.2f}, p={v['p']:.3g}" if isinstance(v, dict) and "R" in v else f"{k}: {v}"
        for k, v in comps.items()
    )

    story = []
    # TITLE
    story.append(Spacer(1, 18 * mm))
    story.append(P("Statistical Regularities in Cocktail Recipes:", S["CoverTitle"]))
    story.append(P("An Exploratory Analysis of CocktailDB<br/>Adapted from the Framework of Universal Culinary Scaling Laws", S["CoverTitle"]))
    story.append(Spacer(1, 6 * mm))
    story.append(P("Research-style exploratory data analysis report", S["CoverSub"]))
    story.append(P("Dataset: CocktailDB (ID, name, category, ingredients, nutrients, ratings, votes, preparation time, cuisine)", S["CoverMeta"]))
    story.append(P("Methodological reference: Bagler, Tewari, Yadav, Singh, Bansal, Dargar, Goel &amp; Sinha, <i>Universal statistical laws governing culinary design</i> (arXiv:2604.28021v1).", S["CoverMeta"]))
    story.append(P("This report does not reproduce the paper’s global-cuisine corpus. It tests which of the paper’s statistical questions can be asked, and which patterns actually appear, in a cocktail-specific dataset.", S["CoverMeta"]))
    story.append(Spacer(1, 8 * mm))
    story.append(P(f"{n:,} raw rows  ·  {n_names:,} unique names  ·  {n_corp:,} recipes in the frequency corpus  ·  {n_ing:,} normalized ingredients", S["CoverMeta"]))
    story.append(PageBreak())

    # PIPELINE / METHODS FRONT MATTER
    story.append(P("How this study was conducted", S["H1"]))
    story.append(P(
        "This front section documents the computational workflow before any scientific results. "
        "It answers three practical questions: how the pipeline was built, what exploratory and preprocessing operations were applied to CocktailDB, "
        "and which libraries implemented each step. Later sections report findings; they do not re-describe the engineering.",
        S["Body"],
    ))

    story.append(P("Design principle", S["H2"]))
    story.append(P(
        "The professor’s paper (Bagler et al., arXiv:2604.28021v1) supplied the <i>questions and estimators</i>, not a template of numbers to recover. "
        "Work therefore began by reading the paper’s Introduction, Figures 1–4, Methods, and Extended Data, then mapping each paper quantity onto CocktailDB columns. "
        "Where a variable was absent (cooking techniques, utensils, instruction steps, reliable cuisine labels, NER attributes, per-serving nutrients), the analysis was marked <b>not testable</b> rather than approximated with a substitute. "
        "Where a variable existed (pipe-delimited ingredients, ratings, votes, prep time, nutrient strings), the paper’s conceptual definition was implemented on this file and the empirical pattern was allowed to agree, differ, or be weak.",
        S["Body"],
    ))

    story.append(P("Project layout and reproducibility", S["H2"]))
    story.append(P(
        "All work lives under <font face='Courier'>eda_project/</font>. The original CSV is copied to <font face='Courier'>data/CocktailDB_raw.csv</font> and is never overwritten. "
        "Scripts write a cleaned table, long ingredient table, wide nutrient table, figures (PNG + vector PDF), CSV summaries, and JSON numerical payloads. "
        "The research PDF is assembled last by reading those JSON files, so exponents and sample sizes in the text are generated rather than typed by hand. "
        "The full run is <font face='Courier'>python scripts/run_all.py</font>, which executes scripts 01–11 in order.",
        S["Body"],
    ))
    layout_rows = [
        ["Path", "Role"],
        ["data/", "Raw CSV (untouched original copy), CocktailDB_clean.csv, ingredients_long.csv, nutrients_wide.csv"],
        ["scripts/", "Numbered pipeline: audit → clean → EDA → Zipf/Heaps/MA → nutrition → co-occurrence → multivariate → PDF"],
        ["figures/", "All numbered figures as PNG (300 dpi) and PDF (vector)"],
        ["tables/ and tables/json/", "CSV summaries and machine-readable results used by the report builder"],
        ["report/", "CocktailDB_EDA_Research_Report.pdf"],
        ["README.md, requirements.txt", "Reproduction notes and Python dependencies"],
    ]
    story.append(table(wrap_cells(layout_rows, S), [38 * mm, 120 * mm]))
    story.append(Spacer(1, 3 * mm))

    story.append(P("Pipeline architecture (what each script does)", S["H2"]))
    story.append(P(
        "The pipeline is linear and idempotent: each stage reads the raw or cleaned table and writes artifacts for downstream stages. "
        "Shared helpers live in <font face='Courier'>paths.py</font>, <font face='Courier'>plot_style.py</font> (academic matplotlib defaults), "
        "<font face='Courier'>ingredient_norm.py</font>, <font face='Courier'>parsers.py</font> (votes, prep time, nutrients), and <font face='Courier'>stats_utils.py</font>.",
        S["Body"],
    ))
    pipe_rows = [
        ["Script", "What it does"],
        ["01_data_audit.py", "Load raw CSV. Shape, dtypes, unique counts, missingness, exact duplicates, Name vs Name.1 identity, Name+Ingredients clones, same-name variants, rating–vote joint missingness, cuisine/category sparsity, paper-to-column mapping."],
        ["02_cleaning.py", "Build the analytical table without mutating the raw file. Drop Name.1. Parse votes and prep minutes. Flag Rating=0 &amp; Votes=0 as unrated. Split ingredients; apply four normalization levels. Extract nutrients. Define the frequency corpus."],
        ["03_basic_eda.py", "Missingness bar and matrix. Recipe-size histogram, violin, ECDF. Top categories (non-missing only). Rating and vote distributions; rating vs log1p(votes). Prep-time distributions and Spearman associations."],
        ["04_ingredient_analysis.py", "Recipe-incidence frequencies f_i (no double-counting within a recipe). Top-30 bars, frequency histogram, log–log rank–frequency plot."],
        ["05_zipf.py", "f(r)~r^(−α) with log–log OLS over multiple rank windows; Clauset-style MLE on the frequency vector; likelihood-ratio checks vs log-normal and exponential."],
        ["06_heaps.py", "100 random recipe orders. Cumulative unique ingredients V(R). Fit β on log–log V vs R (R≥20). Mean curve, 95% permutation band, β histogram."],
        ["07_menzerath.py", "s_i=−log p(i), L=unique ingredients, y=mean information. Scatter, binned means, nonlinear least squares for y=a L^b exp(cL). Sensitivity across normalization and p(i) definitions."],
        ["08_nutrition.py", "Parse two nutrient string formats; map Carbs↔Carbohydrates. Descriptives, completeness, calorie/macro plots, Spearman nutrient matrix, KS fits (log-normal, gamma, Weibull, Gaussian, exponential) on x&gt;0."],
        ["09_cooccurrence.py", "Top-40 co-occurrence heatmap; PMI with a minimum joint-count threshold; network of positive-PMI edges."],
        ["10_multivariate.py", "Pre-specified Spearman pairs (complexity, popularity, nutrients) with bootstrap CIs. Optional PCA on complete-case standardized nutrients."],
        ["12_extended_additions.py", "Prep-time boxplots by top-10 categories; Bayesian vote-adjusted ratings; Zipf log-frequency boxplots by rank stratum."],
        ["11_generate_report.py", "Compose this PDF (ReportLab): narrative, embedded figures, captions, comparison table. Numbers loaded from JSON."],
    ]
    story.append(table(wrap_cells(pipe_rows, S), [36 * mm, 122 * mm]))
    story.append(Spacer(1, 3 * mm))

    story.append(P("First inspection (before any modeling)", S["H2"]))
    story.append(P(
        f"The raw file has {n:,} rows and {A['n_cols']} columns. Header duplication produced pandas names <font face='Courier'>Name</font> and <font face='Courier'>Name.1</font>; these two series were compared programmatically and are identical ({A['name_mismatch_rows']} mismatches). "
        f"Ingredients are 100% present as pipe-delimited free text (quantities still inside the string). Votes are text (comma grouping such as “1,216”). Prep time mixes “3 minutes”, “5 mins”, seconds, hours, days, duplicated phrases, ranges, and unitless numbers. "
        f"Nutrients use two textual grammars: compact “184 Calories|3g Fat|8g Carbs” and colon-style “Calories: 239 kcal|Carbohydrates: 14 g|…”. "
        f"The paper PDF was used to lock estimators: f_i = number of recipes containing ingredient i; Zipf via rank–frequency plus Clauset MLE; Heaps with shuffled incremental sampling; Menzerath–Altmann y(L) = a L^b exp(cL); nutrient log-space KS. "
        f"Cuisine-level laws were abandoned at this stage because Cuisine is {A['missing_pct']['Cuisine']:.1f}% missing.",
        S["Body"],
    ))

    story.append(P("Exploratory data analysis protocol", S["H2"]))
    story.append(P(
        "EDA was treated as a sequence of documented questions, each with an explicit observation count n, not as a gallery of charts. "
        "Univariate work covered recipe size, labelled categories, ratings, votes, and parsed preparation time. "
        "Bivariate work used Spearman rank correlation as the default association measure because votes, times, and nutrients are skewed; Pearson was reported only as a companion on log1p(votes) vs rating. "
        "Bootstrap 95% intervals (400 resamples) accompany key Spearman estimates. "
        "Heavy-tailed variables were shown on both linear and log (or log1p) axes. ECDFs were used for discrete recipe size. "
        "No 3-D plots and no pie charts. matplotlib only, white background, fixed color palette, 300 dpi PNG plus vector PDF. "
        "Every figure in the results sections carries: title, axis labels with units, sample size, and a five-part caption (what it shows, key insight, why it matters, statistical evidence, caveat).",
        S["Body"],
    ))
    eda_rows = [
        ["EDA block", "Operations"],
        ["Missingness", "Percent-missing bars; binary missingness matrix; combination patterns of Category/Nutrients/Ratings/Votes/Prep_Time/Cuisine; joint rating–vote table."],
        ["Duplicates", "Exact row clones vs Name+Ingredients clones vs same name with different ingredients. Only the first two classes were removed from the frequency corpus."],
        ["Recipe structure", "raw vs unique ingredient counts; repeats inside a recipe; histogram, violin/box, ECDF of L."],
        ["Categorical fields", "Category restricted to non-missing rows; long-tail and cumulative share. Cuisine counted and then ruled out for stratified analysis."],
        ["Popularity", "Rating histogram (bounded 0–5); votes linear + log1p; scatter rating vs log1p(votes); low-vote vs high-vote extremeness."],
        ["Prep time", "Parsed minutes; raw + log10 histograms; Spearman vs ingredient count and vs votes. Extremes inspected, not auto-deleted."],
        ["Ingredients", "Incidence ranking; hapax fraction; log–log rank–frequency; co-occurrence and PMI on a top-N set."],
        ["Scaling laws", "Zipf range sensitivity; Heaps permutations; Menzerath binned NLS + residual/sensitivity checks."],
        ["Nutrition", "Format harmonization; completeness; macros; Spearman matrix; candidate distribution KS; PCA if complete cases sufficed."],
    ]
    story.append(table(wrap_cells(eda_rows, S), [36 * mm, 122 * mm]))
    story.append(Spacer(1, 3 * mm))

    story.append(P("Preprocessing decisions (what we changed, and what we refused to change)", S["H2"]))
    story.append(P("<b>Kept untouched.</b> The original CSV. Original Ratings, Votes, Prep_Time, Nutrients, and Ingredients strings remain on the cleaned table beside derived fields.", S["Body"]))
    story.append(P(
        f"<b>Dropped from models only.</b> Redundant <font face='Courier'>Name.1</font>. "
        f"{C['n_exact_duplicate_dropped_for_frequency']} extra exact duplicate rows and "
        f"{C['n_name_ing_duplicate_dropped_for_frequency']} extra Name+Ingredients clones, solely so one scraped formula cannot inflate f_i. "
        f"{A['names_with_different_ingredients']} names with different ingredient lists were retained as variants.",
        S["Body"],
    ))
    story.append(P(
        f"<b>Ratings / votes.</b> Commas stripped; {C['malformed_votes']} malformed vote strings. "
        f"All {C['n_unrated_zero_stars']} rows with Rating=0 also had Votes=0; they were recoded as missing in <font face='Courier'>rating_analyzed</font> / <font face='Courier'>votes_analyzed</font>, not as genuine zero-star scores. "
        "No imputation of ratings, votes, categories, cuisine, or free text.",
        S["Body"],
    ))
    story.append(P(
        f"<b>Preparation time.</b> Tokenized into minutes (seconds/60, hours×60, days×1440; ranges averaged; duplicated phrases de-duplicated when the whole string repeated; unitless numbers treated as minutes). "
        f"Unparsed strings: {C['prep_unparsed']}. Zeros and multi-hour/day values were flagged, not deleted.",
        S["Body"],
    ))
    story.append(P(
        "<b>Ingredients.</b> Split on “|”. Four documented normalization levels: "
        "<i>surface</i> (lowercase/whitespace only); "
        "<i>standard</i> (strip leading/trailing quantities and units; main analyses; Cointreau→orange liqueur and Kahlua→coffee liqueur only as obvious aliases); "
        "<i>moderate</i> (also garnish/prep descriptors); "
        "<i>core</i> (sensitivity only: ice variants and drop “fresh”). "
        "Lime, lime juice, and fresh lime juice were <b>not</b> collapsed. Frequency is distinct recipes, not mention counts.",
        S["Body"],
    ))
    story.append(P(
        "<b>Nutrients.</b> Two parsers (colon labels and compact “value + unit + name”). Carbs and Carbohydrates merged only after confirming both are gram masses. "
        "Vitamin A remains in IU where reported. Serving size is not assumed. Log transforms and KS tests use strictly positive values; zeros are counted separately and excluded from log-space.",
        S["Body"],
    ))

    story.append(P("Libraries and statistical tools", S["H2"]))
    story.append(P(
        "The environment is CPython 3.13. Analyses are ordinary scientific Python; no black-box AutoML. "
        "ReportLab builds the paginated PDF. Pillow measures figure aspect ratios so embedded plots are not stretched.",
        S["Body"],
    ))
    lib_rows = [
        ["Library", "Use in this project"],
        ["pandas / numpy", "Tables, missingness, grouping, frequency corpus, I/O of CSV/JSON."],
        ["matplotlib", "All research figures (histograms, ECDF, log–log plots, heatmaps, PCA scree/projection)."],
        ["scipy", "Spearman/Pearson, skewness, linregress (log–log OLS), curve_fit (Menzerath–Altmann), kstest, candidate distribution MLE."],
        ["powerlaw (Alstott)", "Clauset-style discrete power-law MLE on ingredient frequencies; likelihood-ratio tests vs log-normal and exponential."],
        ["scikit-learn", "StandardScaler + PCA on complete-case nutrient rows only (descriptive, not prediction)."],
        ["networkx", "Positive-PMI co-occurrence graph layout."],
        ["statsmodels", "Available in the environment; core association tests used scipy to keep estimators transparent."],
        ["reportlab / Pillow", "Academic PDF layout, tables, captions, page numbers; non-distorted figure embedding."],
        ["re / unicodedata", "Ingredient quantity/unit stripping; vote commas; prep-time tokens; nutrient format detection."],
    ]
    story.append(table(wrap_cells(lib_rows, S), [42 * mm, 116 * mm]))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "Quality checks after the run: re-execution from the raw CSV; figure files present; JSON values match captions; NaNs excluded from correlations and log transforms; "
        "duplicate formulas not allowed to inflate frequencies; log(x) only for x&gt;0; outliers investigated rather than bulk-deleted; no causal language in captions.",
        S["Body"],
    ))
    story.append(PageBreak())

    # EXECUTIVE SUMMARY
    story.append(P("Executive Summary", S["H1"]))
    story.append(P(
        f"<b>Dataset.</b> CocktailDB contains <b>{n:,} recipe rows</b> and nine columns. "
        f"The two name fields are identical. There are <b>{n_names:,} unique recipe names</b>. "
        f"After removing {C['n_exact_duplicate_dropped_for_frequency']} exact duplicate rows and "
        f"{C['n_name_ing_duplicate_dropped_for_frequency']} additional Name+Ingredients duplicates, "
        f"<b>{n_corp:,} recipes</b> enter frequency analyses. Same-name recipes with different ingredient lists "
        f"({A['names_with_different_ingredients']} names) were retained as variants. "
        f"Major missingness: Category {A['missing_pct']['Category']:.1f}%, Nutrients {A['missing_pct']['Nutrients']:.1f}%, "
        f"Ratings {A['missing_pct']['Ratings']:.1f}%, Votes {A['missing_pct']['Votes']:.1f}%, "
        f"Prep_Time {A['missing_pct']['Prep_Time']:.1f}%, Cuisine {A['missing_pct']['Cuisine']:.1f}%. "
        f"Ingredients are complete.",
        S["Exec"],
    ))
    findings = [
        f"Ingredient usage is concentrated: the most common normalized ingredient is “{top_ing}” ({top_f:,} recipes; {100*I['share_top1']:.1f}% of the corpus). {100*hapax:.1f}% of the vocabulary occurs in only one recipe.",
        f"Rank–frequency curves are heavy-tailed. A log–log OLS Zipf exponent of α ≈ {fmt(alpha,2)} was obtained on ranks 5–500 (descriptive R² = {fmt(Z['primary_ols'].get('r2'),3)}). A Clauset-style power-law fit to the frequency distribution is reported separately and is not treated as automatic confirmation of Zipf’s law.",
        f"Heaps’ law is clearly sublinear: mean β = {fmt(beta,3)} (100 permutations; 95% interval [{fmt(beta_ci[0],3)}, {fmt(beta_ci[1],3)}]). This is close to the paper’s global β ≈ 0.56 but is estimated on a smaller, cocktail-only corpus and is not a target to match.",
        f"Menzerath–Altmann: Spearman correlation between recipe size L and mean ingredient information y(L) is ρ = {fmt(ma_sp,3)}. The paper’s decreasing-then-rising global pattern is not assumed; the fitted MA parameters and R² are reported in §6.3.",
        f"Recipe size is small relative to the paper’s food corpus: mean unique ingredients = {fmt(E['ingredient_count'].get('mean'),2)} (median {fmt(E['ingredient_count'].get('median'),1)}; n = {E['ingredient_count'].get('n'):,}).",
        f"Ratings, where observed, are high and left-censored toward 5 stars (mean {fmt(E['rating'].get('mean'),2)}, median {fmt(E['rating'].get('median'),2)}, n = {rating_n:,}). All {C['n_unrated_zero_stars']} Rating=0 rows have Votes=0 and were treated as unrated.",
        f"Votes are heavy-tailed. Spearman association of votes with rating is ρ = {fmt(E['rating_vs_votes']['spearman'].get('rho'),3)} (n = {E['rating_vs_votes']['spearman'].get('n')}). This is an association, not evidence that votes cause ratings.",
        f"Cuisine cannot support cuisine-level laws: only {cuisine_n:,} non-missing values ({E['cuisine']['pct']:.2f}% of the frequency corpus), with labels that mix drink types and nationalities.",
        f"Category is available for {cat_n:,} recipes ({100*E['category']['coverage_of_all_recipes']:.1f}% of the frequency corpus); category comparisons are conditional on that subset.",
        f"Nutrient strings exist for {A['nutrients_n_nonmissing']:,} recipes ({A['missing_pct']['Nutrients']:.1f}% missing). Log-space KS comparisons are reported per nutrient; log-normality is not claimed globally. Best KS candidates include: {best_gof_txt}.",
        f"Strongest complete-case Spearman associations among the pre-specified multivariate pairs: {strongest_txt or 'see §8'}.",
        "Cooking techniques, utensils, instruction steps, and 26-cuisine stratification from the reference paper cannot be reproduced because those variables are absent.",
    ]
    for i, fnd in enumerate(findings, 1):
        story.append(P(f"<b>{i}.</b> {fnd}", S["BulletBody"]))
    story.append(PageBreak())

    # TOC
    story.append(P("Contents", S["H1"]))
    toc = [
        "How this study was conducted (pipeline, EDA, preprocessing, libraries)",
        "Executive Summary",
        "Abstract",
        "1. Introduction",
        "2. Research Objectives",
        "3. Dataset Description",
        "4. Data Quality and Preprocessing",
        "5. Exploratory Data Analysis",
        "    5.1 Recipe structure",
        "    5.2 Categories",
        "    5.3 Ingredients",
        "    5.4 Ratings and popularity",
        "    5.5 Preparation time",
        "    5.6 Nutritional characteristics",
        "6. Statistical Laws in Cocktail Recipes",
        "    6.1 Zipf analysis",
        "    6.2 Heaps analysis",
        "    6.3 Menzerath–Altmann analysis",
        "    6.4 Nutrient distribution analysis",
        "7. Ingredient Co-occurrence",
        "8. Multivariate Relationships",
        "9. Comparison with the Reference Paper",
        "10. Major Findings",
        "11. Limitations",
        "12. Future Work",
        "13. Conclusion",
        "References",
        "Appendix",
    ]
    for t in toc:
        story.append(P(t, S["TOC"]))
    story.append(P("List of figures. Figures 1–12: data quality and univariate EDA. Figures 13–19: ingredient scaling laws. Figures 20–21: co-occurrence. Figures 22–30: nutrients, log-normality, and PCA.", S["Body"]))
    story.append(PageBreak())

    story.append(P("Abstract", S["AbstractH"]))
    story.append(P(
        f"Bagler and colleagues argue that traditional recipes behave as a compositional symbolic system: ingredient frequencies are Zipf-like, culinary vocabulary grows sublinearly (Heaps’ law), recipe size trades off with average ingredient information (Menzerath–Altmann), and macronutrient amounts are approximately log-normal. "
        f"This study asks whether those regularities appear in CocktailDB, a corpus of {n:,} cocktail-related recipe rows with pipe-delimited ingredients and partially observed ratings, votes, preparation times, categories, cuisines, and nutrient strings. "
        f"Methods were adapted, not copied: frequency is the number of distinct recipes containing a normalized ingredient; Heaps curves use 100 random recipe orders; Menzerath–Altmann uses y(L)=mean[−log p(i)]; nutrient log-normality is tested only on positive extracted values. "
        f"Technique- and cuisine-stratified analyses from the paper are not testable here. "
        f"Cocktail recipes are short (median {fmt(E['ingredient_count'].get('median'),0)} unique ingredients). Ingredient frequencies are heavy-tailed (OLS Zipf α ≈ {fmt(alpha,2)} on a restricted rank range). Vocabulary growth is sublinear (β ≈ {fmt(beta,2)}). "
        f"The Menzerath–Altmann relationship is estimated rather than assumed to match the global food corpus. Nutrient coverage is incomplete and two text formats had to be harmonized. "
        f"The contribution is an honest mapping from a global culinary-law framework onto a cocktail dataset, including negative and non-testable results.",
        S["Body"],
    ))

    story.append(P("1. Introduction", S["H1"]))
    story.append(P(
        "The reference paper treats recipes as symbolic compositions analogous to sentences: discrete culinary units are combined under cultural and practical constraints. In a corpus of 118,083 traditional recipes from 26 cuisines, the authors report Zipf-like ingredient usage (global rank–frequency exponent α ≈ 1.53; cuisine-mean ≈ 1.39), Heaps’ law with β ≈ 0.56 (cuisine-mean ≈ 0.54), a Menzerath–Altmann relation y(L)=a L^b exp(cL) with a global minimum near L ≈ 13, and log-normal macronutrient concentrations. Those claims concern a NER-structured, cuisine-labelled food corpus, not cocktails.",
        S["Body"],
    ))
    story.append(P(
        "Cocktails are a narrower compositional domain: typically few ingredients, repeated base spirits, juices, liqueurs, and garnishes, and recipe sources that often mix blogs, databases, and user reviews. If Zipf/Heaps structure is truly generic to culinary design, a cocktail corpus should show heavy-tailed reuse and sublinear vocabulary growth even without global cuisine coverage. If instead those laws depend on savory cooking, long ingredient lists, or NER-normalized taxonomies, cocktail data may differ—and that difference is scientifically informative.",
        S["Body"],
    ))
    story.append(P(
        "<b>What can and cannot be reproduced.</b> Reproducible in spirit: ingredient frequency, Zipf rank–frequency analysis, Heaps growth, Menzerath–Altmann on recipe size versus mean ingredient information, nutrient distributional tests where values exist, and recipe-size histograms. "
        "Not reproducible: named-entity decomposition of quantity/unit/state; cooking-technique and utensil vocabularies; instruction-step complexity; geographic maps; 26-cuisine exponent distributions; per-serving RecipeDB nutrient standardization; and the paper’s generative simulations as a reproduction. Cuisine in CocktailDB is 97.7% missing and is not a substitute for the paper’s cuisine axis.",
        S["Body"],
    ))

    story.append(P("2. Research Objectives", S["H1"]))
    story.append(P("The objectives are: (i) audit CocktailDB and map paper variables onto observed columns; (ii) quantify missingness without imputing ratings, votes, or text fields; (iii) standardize ingredients with a documented hierarchy and without collapsing lime / lime juice / fresh lime juice; (iv) describe recipe size, category, rating, vote, and preparation-time distributions on observed subsets; (v) test Zipf, Heaps, and Menzerath–Altmann structure; (vi) parse nutrients, assess completeness, and compare candidate distributions; (vii) add co-occurrence and multivariate association analyses that the paper does not emphasize; (viii) state where the cocktail corpus agrees, differs, or cannot be compared.", S["Body"]))

    story.append(P("3. Dataset Description", S["H1"]))
    story.append(P(
        f"The file contains {n:,} rows and {A['n_cols']} columns: Name, Name.1, Category, Ingredients, Nutrients, Ratings, Votes, Prep_Time, Cuisine. "
        f"Name equals Name.1 on every row (mismatches = {A['name_mismatch_rows']}). Name.1 is redundant and is dropped from models. "
        f"Ingredients are pipe-delimited free-text phrases with quantities and units still inside the string (unlike the paper’s NER attributes). "
        f"There is no identifier column beyond the recipe name. Votes are stored as text (including comma grouping). Ratings are numeric on a 0–5 scale.",
        S["Body"],
    ))
    map_rows = [["Paper quantity", "CocktailDB field", "Status"],
                ["Recipe document", "Row; Name", "Present"],
                ["Ingredient identity (NER)", "Derived from Ingredients", "Approximate; not NER"],
                ["Frequency f_i", "Distinct recipes containing i", "Implemented"],
                ["Recipe size L", "unique_ingredient_count", "Implemented"],
                ["Cuisine (26 classes)", "Cuisine", "Present but 97.7% missing"],
                ["Cooking techniques", "—", "Absent"],
                ["Utensils / steps", "—", "Absent"],
                ["Macronutrients per serving", "Nutrients text", "Partial; serving not documented"],
                ["Cook time", "Prep_Time", "Partial; heterogeneous units"]]
    story.append(table(wrap_cells(map_rows, S), [48 * mm, 52 * mm, 58 * mm]))
    story.append(Spacer(1, 3 * mm))

    story.append(P("4. Data Quality and Preprocessing", S["H1"]))
    story.append(P("4.1 Audit of duplicates and redundancy", S["H2"]))
    story.append(P(
        f"Exact duplicate rows: {A['exact_duplicate_rows_beyond_first']} extras ({A['exact_duplicate_row_instances']} rows involved). These are scrape/storage repeats and were dropped from the frequency corpus. "
        f"Name+Ingredients duplicates beyond the first: {A['duplicate_name_plus_ingredients_beyond_first']}. These are the same formula under the same title and were also dropped for frequency counts so that one recipe cannot inflate f_i. "
        f"Duplicate names overall: {A['duplicate_recipe_names_beyond_first']} extra rows; {A['names_with_multiple_rows']} names appear more than once. "
        f"Of those, {A['names_with_different_ingredients']} names have different ingredient strings (legitimate variants, retained) and {A['names_with_identical_ingredients_repeats']} names repeat the same ingredients. "
        f"Name and Name.1 are identical; Name.1 is excluded from analysis.",
        S["Body"],
    ))
    story.append(P("4.2 Missingness", S["H2"]))
    story.append(P(
        f"Ratings and votes are almost a joint field: both present in {A['ratings_and_votes_both_present']:,} rows, both missing in {A['ratings_and_votes_both_missing']:,}, ratings without votes in {A['ratings_present_votes_missing']}, votes without ratings in {A['votes_present_ratings_missing']}. "
        f"This is systematic missingness of a popularity block, not independent gaps. Cuisine is too sparse for stratified laws ({A['cuisine_n_nonmissing']} non-missing). Category missingness ({A['missing_pct']['Category']:.1f}%) means category plots are not globally representative.",
        S["Body"],
    ))
    add_fig(
        story, S, "fig01_missing_by_column",
        "Figure 1. Missing-value percentage by column.",
        f"Each bar is the percentage of the {n:,} rows with a null in that column. Ingredients and both name fields are complete; Cuisine is almost empty.",
        f"Popularity (ratings/votes), category, prep time, and nutrients are majority-missing. Cuisine missingness is {A['missing_pct']['Cuisine']:.1f}%.",
        "Any comparison that ignores missingness would pretend CocktailDB is a complete design matrix comparable to the paper’s curated corpus.",
        f"n = {n:,} rows. Highest missingness: Cuisine {A['missing_pct']['Cuisine']:.1f}%, Nutrients {A['missing_pct']['Nutrients']:.1f}%, Category {A['missing_pct']['Category']:.1f}%, Prep_Time {A['missing_pct']['Prep_Time']:.1f}%, Ratings {A['missing_pct']['Ratings']:.1f}%.",
        "Null encoding is taken as missing; empty strings were not separately treated as a second missing class for these fields.",
    )
    add_fig(
        story, S, "fig02_missingness_matrix",
        "Figure 2. Missingness pattern (downsampled rows).",
        "Black cells are missing. Rows are shown at a regular stride to make blocks visible. Ingredients stay complete while Cuisine is almost continuously missing.",
        "Missingness is structured: large contiguous stretches lack category/nutrients/ratings together, consistent with heterogeneous source tables concatenated into one file.",
        "Systematic missingness implies that nutrient and rating analyses describe source subsets, not a random sample of all cocktail recipes.",
        f"Displayed stride chosen so that ~900 row-samples represent {n:,} recipes. Joint rating–vote presence n = {A['ratings_and_votes_both_present']:,}.",
        "Downsampling can hide single-row anomalies; combination counts in the appendix use the full matrix.",
    )
    story.append(P("4.3 Ratings, votes, and preparation time", S["H2"]))
    story.append(P(
        f"All {C['n_unrated_zero_stars']} rows with Rating = 0 also have Votes = 0. They are coded as unrated (rating_analyzed and votes_analyzed missing), not as genuine zero-star quality. The original columns are preserved. "
        f"Votes such as “1,216” were parsed by removing commas; malformed votes = {C['malformed_votes']}. "
        f"Prep times were parsed into minutes (seconds/60, hours×60, days×1440; ranges averaged; unitless numbers treated as minutes). "
        f"On the frequency corpus, prep-time minutes have min {fmt(C['prep_time_stats_minutes'].get('min'),2)}, median {fmt(C['prep_time_stats_minutes'].get('median'),2)}, mean {fmt(C['prep_time_stats_minutes'].get('mean'),2)}, IQR {fmt(C['prep_time_stats_minutes'].get('iqr'),2)}, P90 {fmt(C['prep_time_stats_minutes'].get('p90'),2)}, P95 {fmt(C['prep_time_stats_minutes'].get('p95'),2)}, max {fmt(C['prep_time_stats_minutes'].get('max'),2)} (n = {C['prep_time_stats_minutes'].get('n')}). "
        f"Extremes include multi-hour and multi-day values and one 336-hour string; they were retained and flagged rather than deleted. Unparsed prep strings: {C['prep_unparsed']}. Zeros: {C['prep_zero']}.",
        S["Body"],
    ))
    story.append(P("4.4 Ingredient normalization", S["H2"]))
    story.append(P(
        f"Four levels were computed. Main analyses use <b>standard</b> (lowercase, whitespace, strip leading/trailing quantities and units; Cointreau→orange liqueur and Kahlua→coffee liqueur only as obvious aliases). Moderate additionally strips garnish/prep descriptors. Core is sensitivity-only (ice variants; drop “fresh”). "
        f"Vocabulary at standard level: {C['vocab_by_level']['standard']['n_unique']:,} unique strings from {C['vocab_by_level']['standard']['n_mentions']:,} mentions. Surface unique strings: {C['vocab_by_level']['surface']['n_unique']:,}. Core unique: {C['vocab_by_level']['core']['n_unique']:,}. "
        f"Lime versus lime juice is not collapsed.",
        S["Body"],
    ))

    story.append(P("5. Exploratory Data Analysis", S["H1"]))
    story.append(P("5.1 Recipe structure", S["H2"]))
    ic = E["ingredient_count"]
    story.append(P(
        f"Observation: cocktail formulas are short. Mean unique ingredients = {fmt(ic.get('mean'),2)}, median = {fmt(ic.get('median'),2)}, IQR = {fmt(ic.get('iqr'),2)}, range {fmt(ic.get('min'),0)}–{fmt(ic.get('max'),0)} (n = {ic.get('n'):,}). "
        f"The paper’s global food corpus peaked near 8–12 ingredients with mean about 10; cocktails sit well below that characteristic scale. "
        f"Interpretation: drink recipes are composed around a small number of components. Limitation: unique_ingredient_count depends on normalization; residual quantity fragments would bias counts upward.",
        S["Body"],
    ))
    add_fig(story, S, "fig03_ingredient_count_hist", "Figure 3. Distribution of unique ingredients per recipe.",
            f"Histogram of L on the frequency corpus (n = {ic.get('n'):,}). A vertical median and mean are overlaid.",
            f"Most recipes use about {fmt(ic.get('median'),0)} unique ingredients; the right tail reaches {fmt(ic.get('max'),0)}.",
            "Recipe complexity in this corpus is primarily low-dimensional, which will later constrain Menzerath–Altmann (few large-L bins).",
            f"n = {ic.get('n'):,}; mean = {fmt(ic.get('mean'),2)}; median = {fmt(ic.get('median'),2)}; SD = {fmt(ic.get('std'),2)}.",
            "L is unique normalized ingredients, not raw pipe tokens.")
    add_fig(story, S, "fig04_ingredient_count_violin", "Figure 4. Spread of recipe size.",
            "Violin plus boxplot of unique ingredient counts.",
            f"Dispersion is modest (IQR {fmt(ic.get('iqr'),2)}); outliers exist but do not dominate the mass.",
            "Outlier long recipes exist (punches, pitchers, garnished showpieces) but are uncommon.",
            f"n = {ic.get('n'):,}; min = {fmt(ic.get('min'),0)}; max = {fmt(ic.get('max'),0)}.",
            "Boxplot whiskers follow the default matplotlib convention; outliers are plotted, not removed.")
    add_fig(story, S, "fig05_ingredient_count_ecdf", "Figure 5. ECDF of recipe size.",
            "The empirical CDF of L shows how quickly probability mass accumulates at small sizes.",
            f"A large fraction of recipes have L at or below the median of {fmt(ic.get('median'),0)}.",
            "ECDFs avoid binning artifacts in a discrete, skewed count variable.",
            f"n = {ic.get('n'):,}.",
            "Ties at integer L produce vertical jumps.")

    story.append(P("5.2 Categories", S["H2"]))
    cat = E["category"]
    story.append(P(
        f"Category is observed for {cat['n_nonmissing']:,} recipes ({100*cat['coverage_of_all_recipes']:.1f}% of the frequency corpus), with {cat['n_unique']} distinct labels. "
        f"The top five categories account for {100*cat['top5_share']:.1f}% of labelled recipes; the top 20 account for {100*cat['top20_share']:.1f}%. "
        f"Labels mix glassware, flavor families, and spirit families (shots, sours, margaritas, highballs). Missing Category is not treated as a category. Conclusions are conditional on the labelled subset.",
        S["Body"],
    ))
    add_fig(story, S, "fig06_top_categories", "Figure 6. Top 20 categories by recipe count.",
            f"Counts among recipes with non-missing Category (n = {cat['n_nonmissing']:,}).",
            f"The leading labelled class is dominated by a long-tailed remainder: {cat['n_unique']} labels overall.",
            "Category is a noisy ontology, useful for describing the labelled slice, not for claiming a global taxonomy of cocktails.",
            f"n_labelled = {cat['n_nonmissing']:,}; coverage = {100*cat['coverage_of_all_recipes']:.1f}% of {n_corp:,} frequency-corpus recipes; top-20 share = {100*cat['top20_share']:.1f}%.",
            "Do not compare categories as if every recipe were labelled.")

    story.append(P("5.3 Ingredients", S["H2"]))
    story.append(P(
        f"Using standard normalization, {n_ing:,} distinct ingredients appear in {I['n_recipes']:,} recipes. "
        f"“{top_ing}” occurs in {top_f:,} recipes ({100*I['share_top1']:.1f}%). Hapax ingredients (frequency 1) are {I['hapax_n']:,} ({100*hapax:.1f}% of vocabulary). "
        f"This is the same conceptual frequency as the paper: f_i = number of distinct recipes containing i, with within-recipe repeats not double-counted.",
        S["Body"],
    ))
    add_fig(story, S, "fig13_top30_ingredients", "Figure 13. Top 30 ingredients by recipe frequency.",
            f"Bars are f_i for the 30 most common standard-normalized ingredients (n_recipes = {I['n_recipes']:,}).",
            f"A small set of bases, juices, sweeteners, bitters, and ice-like items dominate. The leader is {top_ing} with f = {top_f:,}.",
            "Preferential reuse of a core bar vocabulary is the cocktail analogue of the paper’s salt/onion/butter/flour/oil dominance in food.",
            f"n_recipes = {I['n_recipes']:,}; vocabulary = {n_ing:,}; top-10 share of all frequency mass = {100*I['share_top10']:.1f}%.",
            "Normalization aliases (e.g., Cointreau as orange liqueur) slightly inflate some totals; lime juice is kept distinct from lime.")
    add_fig(story, S, "fig14_ingredient_frequency_hist", "Figure 14. Distribution of ingredient frequencies.",
            "Most ingredients are rare; a thin tail of high-frequency items sits far to the right.",
            f"{100*hapax:.1f}% of ingredients appear once. Mean frequency = {fmt(I['frequency_summary'].get('mean'),2)}; median = {fmt(I['frequency_summary'].get('median'),2)}.",
            "This is the size distribution that Zipf and Heaps later summarize: reuse of few items plus a long tail of novelty.",
            f"n_ingredients = {n_ing:,}.",
            "The linear-axis histogram compresses the tail; the rank–frequency plot is the appropriate scaling view.")
    add_fig(story, S, "fig15_rank_frequency_loglog", "Figure 15. Rank–frequency plot on log–log axes.",
            "Each point is an ingredient: rank r versus recipe frequency f(r).",
            "The cloud declines over several decades and is curved rather than a single perfect line, which already warns against an unrestricted power-law claim.",
            "Heavy tails mean a bartender’s core shelf covers many recipes while rare modifiers create diversity.",
            f"n = {n_ing:,} ingredients; n_recipes = {I['n_recipes']:,}.",
            "Visual linearity is not a statistical test; see Figure 16.")

    story.append(P("5.4 Ratings and popularity", S["H2"]))
    rt, vt = E["rating"], E["votes"]
    rv = E["rating_vs_votes"]
    story.append(P(
        f"Ratings (excluding unrated zeros): n = {rt.get('n'):,}, mean = {fmt(rt.get('mean'),3)}, median = {fmt(rt.get('median'),3)}, SD = {fmt(rt.get('std'),3)}, IQR = {fmt(rt.get('iqr'),3)}, skewness = {fmt(rt.get('skewness'),3)}. "
        f"The support is bounded by 5, so unbounded continuous distribution fitting is not used as a primary model. "
        f"Votes: n = {vt.get('n'):,}, median = {fmt(vt.get('median'),1)}, mean = {fmt(vt.get('mean'),1)}, max = {fmt(vt.get('max'),0)}, skewness = {fmt(vt.get('skewness'),2)}. "
        f"Pearson(rating, log1p votes) r = {fmt(rv['pearson'].get('r'),3)}, p = {pval(rv['pearson'].get('p'))}, n = {rv['pearson'].get('n')}. "
        f"Spearman(rating, votes) ρ = {fmt(rv['spearman'].get('rho'),3)}, p = {pval(rv['spearman'].get('p'))}, n = {rv['spearman'].get('n')}; bootstrap 95% CI {rv['spearman_ci'].get('ci95')}. Spearman is primary because votes are heavy-tailed. "
        f"Low-vote recipes (≤3 votes, n = {rv['n_votes_le_3']}) have more extreme ratings (share of ratings ≤2 or ≥4.9 = {fmt(100*(rv.get('extreme_rating_share_low_votes') or 0),1)}%) than high-vote recipes (≥50, n = {rv['n_votes_ge_50']}, share {fmt(100*(rv.get('extreme_rating_share_high_votes') or 0),1)}%).",
        S["Body"],
    ))
    add_fig(story, S, "fig07_rating_distribution", "Figure 7. Rating distribution.",
            f"Histogram of analyzed ratings on 0–5 (n = {rt.get('n'):,}), excluding Rating=Votes=0.",
            f"Mass piles near 4–5 stars (median {fmt(rt.get('median'),2)}). The scale is compressed at the top.",
            "High means do not imply uniformly excellent recipes; they can reflect selection, interface defaults, and small-n 5-star ratings.",
            f"mean = {fmt(rt.get('mean'),3)}; SD = {fmt(rt.get('std'),3)}; IQR = {fmt(rt.get('iqr'),3)}; skewness = {fmt(rt.get('skewness'),3)}.",
            "Bounded discrete/ordinal ratings; unrated zeros excluded by design.")
    add_fig(story, S, "fig08_votes_distribution", "Figure 8. Votes on linear and log1p scales.",
            f"Left: raw vote counts. Right: log1p(Votes). n = {vt.get('n'):,}.",
            f"Popularity is long-tailed (mean {fmt(vt.get('mean'),1)} ≫ median {fmt(vt.get('median'),1)}; max {fmt(vt.get('max'),0)}).",
            "A few recipes attract most attention; vote counts are a poor proxy for objective quality.",
            f"skewness = {fmt(vt.get('skewness'),2)}; P90 = {fmt(vt.get('p90'),1)}.",
            "Votes exist only for the popularity-observed subset.")
    add_fig(story, S, "fig09_rating_vs_votes", "Figure 9. Rating versus log1p(Votes).",
            "Each point is a recipe with both an analyzed rating and vote count.",
            f"Association is positive but modest (Spearman ρ = {fmt(rv['spearman'].get('rho'),3)}). Low-n ratings fan out to 1 and 5.",
            "Highly voted recipes are not guaranteed higher ratings; they do tend to occupy a narrower high-rating band, consistent with averaging.",
            f"Spearman ρ = {fmt(rv['spearman'].get('rho'),3)}, p = {pval(rv['spearman'].get('p'))}, n = {rv['spearman'].get('n')}; Pearson(r, log1p votes) = {fmt(rv['pearson'].get('r'),3)}.",
            "No causal claim: better-known recipes may be better, or only more rated.")
    story.append(P("Vote-adjusted ratings", S["H3"]))
    story.append(P(
        f"Following the extended recipes EDA notebook, a Bayesian-style shrinkage estimator is "
        f"adj = (V·R + m·C) / (V + m) with m = {X['bayes_m']:.0f} and C = global mean analyzed rating = {fmt(X['bayes_C'],3)} "
        f"(n = {X['bayes_n']:,} recipes with both rating and votes after unrated-zero exclusion). "
        "This does not create new information; it down-weights 1-vote 5-star recipes relative to well-voted ones.",
        S["Body"],
    ))
    adj_header = ["Name", "Rating", "Votes", "Adj. rating"]
    adj_rows = [adj_header]
    for rec in X.get("top10_adj", [])[:10]:
        adj_rows.append(
            [
                rec.get("name", ""),
                fmt(rec.get("rating_analyzed"), 2),
                fmt(rec.get("votes_analyzed"), 0),
                fmt(rec.get("adj_rating"), 3),
            ]
        )
    story.append(table(wrap_cells(adj_rows, S), [78 * mm, 24 * mm, 24 * mm, 32 * mm]))
    story.append(P("Table. Top 10 recipes by vote-adjusted rating (m = 10).", S["Caption"]))
    story.append(Spacer(1, 3 * mm))

    story.append(P("5.5 Preparation time", S["H2"]))
    pr = E["prep"]
    ps = E["prep_vs_size"]
    pv = E["prep_vs_votes"]
    story.append(P(
        f"Parsed prep time (minutes) on the frequency corpus where available: n = {pr.get('n'):,}, median = {fmt(pr.get('median'),2)}, mean = {fmt(pr.get('mean'),2)}, max = {fmt(pr.get('max'),1)}. "
        f"Spearman(prep time, ingredient count) ρ = {fmt(ps['spearman'].get('rho'),3)}, p = {pval(ps['spearman'].get('p'))}, n = {ps['n']}. "
        f"Spearman(prep time, votes) ρ = {fmt(pv['spearman'].get('rho'),3)}, p = {pval(pv['spearman'].get('p'))}, n = {pv['n']}. "
        f"Neither association is interpreted as a production function or a popularity mechanism.",
        S["Body"],
    ))
    add_fig(story, S, "fig10_prep_time", "Figure 10. Preparation-time distribution.",
            f"Raw minutes (left) and log10 of positive times (right). n = {pr.get('n'):,}.",
            f"Typical times are a few minutes (median {fmt(pr.get('median'),1)}), with a long right tail including hours/days.",
            "Most cocktails are quick to assemble; extreme values may mix infusion/rest times with active prep or parsing artifacts (e.g., duplicated phrases, 336 hours).",
            f"mean = {fmt(pr.get('mean'),2)}; P95 = {fmt(pr.get('p95'),2)}; max = {fmt(pr.get('max'),1)}.",
            "Unitless numbers were assumed to be minutes; that assumption is documented, not verified by the source.")
    add_fig(story, S, "fig11_prep_vs_ingredient_count", "Figure 11. Preparation time versus ingredient count.",
            "Scatter of minutes against unique ingredient count.",
            f"The rank correlation is {fmt(ps['spearman'].get('rho'),3)} (n = {ps['n']}).",
            "A weak relationship would mean longer drinks are not simply those with more ingredients (batching, chilling, or infusion can dominate).",
            f"Spearman ρ = {fmt(ps['spearman'].get('rho'),3)}, p = {pval(ps['spearman'].get('p'))}; 95% bootstrap CI {ps['spearman_ci'].get('ci95')}.",
            "Outliers in time can dominate Pearson correlation; Spearman is used.")
    add_fig(story, S, "fig12_prep_vs_votes", "Figure 12. Popularity versus preparation time.",
            "log1p(Votes) against parsed minutes.",
            f"Spearman ρ = {fmt(pv['spearman'].get('rho'),3)} (n = {pv['n']}).",
            "Even a statistically nonzero ρ would not show that faster drinks become popular; source confounding is likely.",
            f"ρ = {fmt(pv['spearman'].get('rho'),3)}, p = {pval(pv['spearman'].get('p'))}; CI {pv['spearman_ci'].get('ci95')}.",
            "Complete cases only; prep and votes are both missing for many rows.")
    add_fig(
        story, S, "fig31_prep_time_by_category_boxplot",
        "Figure 31. Preparation time by top 10 categories (boxplot).",
        f"Boxplots of parsed minutes in the ten most frequent non-missing categories (n = {X['boxplot_n_total']:,} recipes with both category and prep time). The vertical axis is clipped near the 99th percentile ({fmt(X['boxplot_p99'],1)} min) so a few extreme infusions do not compress the boxes.",
        f"Medians remain short in every leading category (typical medians {', '.join(f'{k}: {v:.1f} min' for k, v in list(X.get('boxplot_median_minutes', {}).items())[:4] if v is not None)}). Outliers exist in several classes.",
        f"Category-level prep time is the comparison the extended EDA notebook emphasized and that this report previously omitted. Categories are the ten most frequent among recipes that have both Category and parsed prep time (not the global top-10 labels, because category and prep time rarely co-occur).",
        f"Top categories = {', '.join(X.get('boxplot_categories', [])[:10])}. Per-category n = {X.get('boxplot_n_per_category')}.",
        "Do not treat these ten bars as a global ranking of cocktail types; Category coverage is incomplete and the y-cap hides the most extreme points.",
    )

    story.append(P("5.6 Nutritional characteristics", S["H2"]))
    story.append(P(
        f"Nutrient strings are present for {A['nutrients_n_nonmissing']:,} / {n:,} recipes ({A['missing_pct']['Nutrients']:.1f}% missing). Two formats occur: compact “184 Calories|3g Fat|8g Carbs” and colon-style “Calories: 239 kcal|Carbohydrates: 14 g|…”. Carbs and Carbohydrates were mapped to one carbohydrates variable after checking that both are gram masses in the observed text. "
        f"The file does not state per-serving standardization. Completeness and moments for each extracted nutrient are in §6.4 and the appendix tables. PCA, if performed, uses complete cases only.",
        S["Body"],
    ))

    # Section 6
    story.append(P("6. Statistical Laws in Cocktail Recipes", S["H1"]))
    story.append(P("6.1 Zipf analysis", S["H2"]))
    cl = Z["clauset_on_frequencies"]
    story.append(P(
        f"Model: f(r) ~ r^{{-α}} on ingredient ranks. Primary descriptive fit is log–log OLS on r ∈ [5, {Z['primary_range']['rmax']}], giving α = {fmt(alpha,3)}, R² = {fmt(Z['primary_ols'].get('r2'),3)}, n_points = {Z['primary_ols'].get('n')}. "
        f"The unrestricted full-range OLS α = {fmt(Z.get('full_range_alpha'),3)} with R² = {fmt(Z.get('linear_full_range_r2'),3)}, which is a reminder that curvature at the head and far tail moves the exponent. "
        f"Following Clauset et al. as in the paper’s Methods, a discrete power law was also fitted to the vector of frequencies (P(f) ~ f^{{-α_freq}}), which is not identical to the rank–frequency exponent. MLE α_freq = {fmt(cl.get('alpha_freq_dist'),3)}, x_min = {fmt(cl.get('xmin'),2)}, KS = {fmt(cl.get('ks'),3)}, n_tail = {cl.get('n_in_tail')}. "
        f"Likelihood-ratio comparisons versus alternatives: {lr_txt}. Positive R favors the power law in the Alstott implementation; p-values near 1 do not automatically validate a power law over the whole range. "
        f"A heavy tail in cocktails means a small core bar (spirits, citrus, sugar, bitters, ice) is reused constantly, while a long tail of liqueurs, garnishes, and branded products supplies diversity. The fit is reported as Zipf-like, not as a proven unique generative law.",
        S["Body"],
    ))
    add_fig(story, S, "fig16_zipf_fit", "Figure 16. Empirical rank–frequency distribution and fitted Zipf relation.",
            "Points: all ingredients. Line: OLS log–log fit on the primary rank window.",
            f"α ≈ {fmt(alpha,2)} on r ∈ [5, {Z['primary_range']['rmax']}]. The empirical curve is heavy-tailed but not a perfect straight line.",
            "If a few ingredients dominate, cocktail “vocabulary” is reusable and predictable; the tail still allows innovation.",
            f"OLS α = {fmt(alpha,3)}, R² = {fmt(Z['primary_ols'].get('r2'),3)}, n = {Z['primary_ols'].get('n')}. Clauset α_freq = {fmt(cl.get('alpha_freq_dist'),3)}, xmin = {fmt(cl.get('xmin'),2)}.",
            "R² is descriptive. Range sensitivity is tabulated in zipf_range_sensitivity.csv. Do not equate α with the paper’s 1.53 without noting corpus differences.")
    add_fig(
        story, S, "fig32_zipf_rank_stratum_boxplot",
        "Figure 32. Zipf diagnostic: log-frequency boxplots by rank stratum.",
        "Each box is the distribution of log10 recipe-frequency for ingredients in a rank window (1–10, 11–50, 51–200, 201–1000, >1000).",
        f"Median log-frequency falls across strata ({', '.join(f'{k}: {v:.2f}' for k, v in X.get('zipf_stratum_median_log10f', {}).items())}), which is the boxplot view of the same heavy tail shown on the log–log rank plot.",
        "This is a compact way to see that a handful of head ingredients sit far above a long body of rare items, without claiming a unique power-law exponent.",
        f"Stratum sizes n = {X.get('zipf_stratum_n')}.",
        "Rank bins are analyst choices. They illustrate Zipf-like decay; they are not a substitute for the MLE/OLS fits in Figure 16.",
    )

    story.append(P("6.2 Heaps analysis", S["H2"]))
    Hs = H["standard"]
    story.append(P(
        f"V(R) is the number of distinct standard-normalized ingredients after R recipes. {Hs['n_shuffle']} random permutations were used. "
        f"Mean β = {fmt(Hs['beta_mean'],4)} (SD {fmt(Hs['beta_std'],4)}; 95% permutation interval [{fmt(Hs['beta_ci95'][0],4)}, {fmt(Hs['beta_ci95'][1],4)}]); mean log–log R² = {fmt(Hs['r2_mean'],4)}. "
        f"β &lt; 1 is sublinear growth: new recipes keep introducing ingredients, but the marginal discovery rate declines. "
        f"The paper’s global β ≈ 0.56 is a reference point, not a target. Cocktail β ≈ {fmt(Hs['beta_mean'],2)} can differ because of domain (drinks vs meals), corpus size ({Hs['n_recipes']:,} vs 118,083), normalization, and source mix. "
        f"Sensitivity: moderate β = {fmt(H['moderate']['beta_mean'],3)}; core β = {fmt(H['core']['beta_mean'],3)}.",
        S["Body"],
    ))
    add_fig(story, S, "fig17_heaps_curve", "Figure 17. Heaps curve with permutation band.",
            f"Mean V(R) and 95% band across {Hs['n_shuffle']} shuffles, log–log axes, with a power-law overlay.",
            f"Growth is sublinear (β ≈ {fmt(Hs['beta_mean'],3)}); the band is tight, so ordering noise is small relative to the trend.",
            "Cocktail innovation continues (the curve still rises at the corpus end) but with diminishing new-ingredient returns.",
            f"β_mean = {fmt(Hs['beta_mean'],4)}; 95% interval [{fmt(Hs['beta_ci95'][0],4)}, {fmt(Hs['beta_ci95'][1],4)}]; final mean V = {fmt(Hs['final_vocab_mean'],1)}; n_recipes = {Hs['n_recipes']:,}.",
            "Fits use R ≥ 20 to reduce the discrete start-up; K is a nuisance scale parameter.")
    add_fig(story, S, "fig18_heaps_beta_hist", "Figure 18. Distribution of β across permutations.",
            "Histogram of log–log OLS exponents, one per shuffle.",
            f"β estimates concentrate tightly around {fmt(Hs['beta_mean'],3)} (SD {fmt(Hs['beta_std'],4)}).",
            "The Heaps exponent is a stable corpus property, not an artifact of one recipe order.",
            f"n_shuffle = {Hs['n_shuffle']}; mean R² = {fmt(Hs['r2_mean'],4)}.",
            "Least-squares on log V vs log R is the paper’s estimator; it is not maximum likelihood.")

    story.append(P("6.3 Menzerath–Altmann analysis", S["H2"]))
    story.append(P(
        f"Following the paper, p(i) = f_i / Σ f_j, s_i = −log p(i), L = unique ingredients, y = mean s_i in the recipe. "
        f"On standard normalization, n = {M['standard']['n_recipes']:,}, Spearman(L, y) = {fmt(ma_sp,3)}. "
        f"Binned MA fit y(L)=a L^b exp(cL): a = {fmt(ma_fit.get('a'),3)}, b = {fmt(ma_fit.get('b'),3)}, c = {fmt(ma_fit.get('c'),3)}, R² = {fmt(ma_fit.get('r2'),3)}, n_bins = {ma_fit.get('n_points')}. "
        f"The paper’s global fit (a=13.16, b=−0.26, c=−0.019, R²=0.99, minimum near L≈13) lives on a length range cocktails barely populate. If y(L) is flat, increasing, or poorly fitted, that is a result: short drink recipes may not exhibit the same complexity–length trade-off as 10-ingredient meals. "
        f"Sensitivity (Spearman): moderate {fmt(M['moderate']['spearman_L_y'],3)}; core {fmt(M['core']['spearman_L_y'],3)}; p(i)=f_i/N_recipes {fmt(M['sensitivity_p_i_over_N_recipes']['spearman'],3)}.",
        S["Body"],
    ))
    add_fig(story, S, "fig19_menzerath", "Figure 19. Average ingredient information versus recipe size.",
            "Grey points: recipes. Blue: binned means with SE bars and bin counts. Orange: MA functional fit on bins with n≥5.",
            f"Spearman ρ(L, y) = {fmt(ma_sp,3)}. The MA R² on bins is {fmt(ma_fit.get('r2'),3)}.",
            "A decreasing y(L) would mean longer drinks pad with common ingredients; an increasing or flat curve would differ from the paper’s efficiency–expressivity story.",
            f"n_recipes = {M['standard']['n_recipes']:,}; L range {M['standard']['L_summary']['min']}–{M['standard']['L_summary']['max']} (median {M['standard']['L_summary']['median']}). a,b,c = {fmt(ma_fit.get('a'),2)}, {fmt(ma_fit.get('b'),2)}, {fmt(ma_fit.get('c'),3)}; R² = {fmt(ma_fit.get('r2'),3)}.",
            "Few recipes have L near 13, so a turning point at the paper’s scale cannot be identified even if the functional form is forced.")

    story.append(P("6.4 Nutrient distribution analysis", S["H2"]))
    story.append(P(
        f"Positive-valued extracted nutrients were compared to log-normal, gamma, Weibull, Gaussian, and exponential laws via KS distance (smaller is better). "
        f"Calories: n+ = {cal_gof.get('n_positive')}, log-skewness = {fmt(cal_gof.get('log_skewness'),3)}, best = {cal_gof.get('best')}. "
        f"Carbohydrates: n+ = {carb_gof.get('n_positive')}, log-skewness = {fmt(carb_gof.get('log_skewness'),3)}, best = {carb_gof.get('best')}. "
        f"The paper reported mean KS 0.0727 for log-normal on meal macronutrients. Cocktail nutrients are sparser, possibly not per serving, and include zeros (especially protein/fat) that are excluded from log tests. Log-normality is supported only where KS and log-skewness jointly agree—not because a histogram looks bell-shaped.",
        S["Body"],
    ))
    add_fig(story, S, "fig22_nutrient_completeness", "Figure 22. Nutrient completeness.",
            f"Percent of all {n:,} recipes with a parsed value for each nutrient.",
            "Even calories, the most common field, cover only a minority of the full table; micronutrients are rarer.",
            "Nutrient EDA is a study of the nutrient-reporting subset, which may be biased toward recipe sites that compute nutrition panels.",
            f"Nutrient strings present: {A['nutrients_n_nonmissing']:,} ({100-A['missing_pct']['Nutrients']:.1f}% of rows have a non-null Nutrients field).",
            "A non-null string can still omit individual nutrients.")
    add_fig(story, S, "fig23_calories", "Figure 23. Calories distribution.",
            "Histogram of extracted calorie values as reported.",
            "The distribution is right-skewed with extreme high values that may reflect pitchers, multiple servings, or parsing/source errors—not typical single-glass cocktails.",
            "Calories cannot be treated as a standardized per-drink nutrient without serving metadata.",
            f"See nutrient_descriptives.csv for n, mean, median, SD, IQR, min, max.",
            "Zeros and missing are excluded from this histogram if non-finite.")
    add_fig(story, S, "fig24_macros", "Figure 24. Macronutrient distributions.",
            "Side-by-side histograms of carbohydrates, protein, and fat in grams where extracted.",
            "Protein is often near zero in drinks; carbohydrates (sugars/juices) and occasional fats (cream, egg, dairy liqueurs) differ sharply.",
            "Cocktail macronutrient structure is not interchangeable with cooked-meal macronutrients in the paper.",
            "Sample sizes differ by nutrient; see Figure 22 and descriptives table.",
            "Units are grams as parsed; cream-based drinks drive fat tails.")
    add_fig(story, S, "fig25_nutrient_corr", "Figure 25. Nutrient Spearman correlation matrix.",
            "Pairwise complete-case Spearman correlations among nutrients with ≥80 observations.",
            "Positive associations among energy-related fields (calories, carbohydrates, sugar, fat) are expected arithmetically if they co-occur on the same panel, not as a biological law.",
            "Correlations are descriptive of reported panels.",
            "Spearman chosen because of skew and outliers.",
            "Pairwise deletion means each cell has its own n.")
    add_fig(story, S, "fig26_nutrients_original", "Figure 26. Original-scale nutrient distributions.",
            "Positive observations for calories, carbohydrates, protein, fat, sugar, and sodium when n+ is sufficient.",
            "All are right-skewed on the original scale.",
            "Skew is why the paper examines log space.",
            "n+ listed in 08_nutrition.json per nutrient.",
            "Zeros excluded.")
    add_fig(story, S, "fig27_nutrients_log", "Figure 27. Log-transformed nutrient distributions.",
            "Natural logs of strictly positive values.",
            f"Log-skewness near 0 would support log-normal symmetry; observed values include calories {fmt(cal_gof.get('log_skewness'),3)} and carbohydrates {fmt(carb_gof.get('log_skewness'),3)}.",
            "Translational invariance across macronutrients (paper Fig. 3b) is only weakly testable with three incomplete cocktail macros.",
            "Log transform applied only for x>0.",
            "Visual unimodality is not a KS test.")
    add_fig(story, S, "fig28_distribution_gof", "Figure 28. Distribution-fit comparison (KS distances).",
            "Rows: nutrients. Columns: candidate laws. Cell text is KS D.",
            f"Best fits by nutrient: {best_gof_txt}. Log-normal is not automatically best for every cocktail nutrient.",
            "This is the paper’s GOF logic applied honestly to drinks data.",
            "D is the KS statistic on positive observations with floc=0 for skewed candidates where used.",
            "KS on large n flags tiny deviations; ranking of D is more relevant than a binary p-value.")

    story.append(P("7. Ingredient Co-occurrence", S["H1"]))
    story.append(P(
        f"Beyond the paper, co-occurrence was counted among the top {CO['top_n']} ingredients. PMI uses p(i,j)/(p(i)p(j)) with a minimum co-occurrence of {CO['min_cooccurrence']} recipes to limit rare-event inflation. "
        f"The network retains positive PMI edges (n_edges = {CO['n_edges']}). Clusters reflect recipe conventions (e.g., spirit+citrus+sweetener, bitters+sugar, cream+chocolate liqueurs) rather than measured flavor-compound pairing. Co-occurrence is not causality and is not food-pairing chemistry.",
        S["Body"],
    ))
    add_fig(story, S, "fig20_cooccurrence_heatmap", "Figure 20. Co-occurrence heatmap (top ingredients).",
            f"Cell (i,j) is the number of recipes containing both ingredients among the top {CO['top_n']}.",
            "Darker cells mark bar-standard pairs (citrus with spirits; sugar with citrus; ice with many bases).",
            "These pairs describe recipe incidence, the combinatorial skeleton of the cocktail corpus.",
            f"n_recipes in long table = {CO['n_recipes']:,}.",
            "Top-N selection conditions on frequency, so rare but culturally important pairs are absent.")
    add_fig(story, S, "fig21_association_network", "Figure 21. Positive-PMI association network.",
            f"Nodes: top {CO['top_n']} ingredients (size ~ frequency). Edges: co-occurrence ≥ {CO['min_cooccurrence']} and PMI > 0.4.",
            f"Highest-PMI edges include: {', '.join(e['a']+'–'+e['b']+' (PMI='+fmt(e['pmi'],2)+')' for e in CO.get('top_pmi_edges', [])[:6])}.",
            "Network clusters are usage cliques, useful for generating hypotheses, not for asserting compatibility.",
            f"n_edges = {CO['n_edges']}.",
            "Thresholds are analyst choices; they hide weak ties.")

    story.append(P("8. Multivariate Relationships", S["H1"]))
    story.append(P(
        "Pre-specified pairs linked complexity (ingredient count, prep time), popularity (votes, ratings), and nutrients (calories, sugar, protein). Spearman correlations with bootstrap CIs are stored in multivariate_spearman.csv. "
        f"Largest |ρ| among those pairs: {strongest_txt or 'insufficient overlap'}. "
        "Effect sizes are interpreted over p-values because n can be large in some complete-case slices and tiny in nutrient slices. No pair is treated as a causal graph.",
        S["Body"],
    ))
    add_fig(story, S, "fig_multivariate_pairs", "Figure. Selected multivariate scatterplots.",
            "Complete-case scatters for ingredient count, calories, sugar, protein, rating, votes, and prep time.",
            "Visual structure is weak to moderate; nutrient axes are dominated by skew and a smaller n.",
            "Cocktail ‘complexity’ is not a strong linear predictor of reported nutrition or popularity in this file.",
            f"See multivariate_spearman.csv; strongest listed above.",
            "Each panel has its own complete-case n.")
    pca = MV.get("pca") or {}
    if pca.get("explained_variance_ratio"):
        add_fig(story, S, "fig29_pca_variance", "Figure 29. PCA explained variance.",
                f"Scree of standardized nutrients on n = {pca.get('n_complete'):,} complete cases, variables = {pca.get('variables')}.",
                f"PC1 explains {100*pca['explained_variance_ratio'][0]:.1f}% and PC2 {100*pca['explained_variance_ratio'][1]:.1f}%.",
                "PCA is a descriptive compression of co-reported nutrient panels, not a latent ‘health’ index.",
                f"Cumulative variance in first two PCs = {100*pca['cumulative'][1]:.1f}%.",
                "Complete-case selection biases toward richer nutrition labels.")
        add_fig(story, S, "fig30_pca_projection", "Figure 30. PCA projection.",
                "Each point is a recipe in the complete nutrient subset.",
                "Spread along PC1 typically aligns with overall magnitude (calories/macros) if loadings share sign.",
                f"PC1 loadings: {pca.get('loadings_pc1')}.",
                f"n = {pca.get('n_complete'):,}.",
                "Do not cluster-interpret without a pre-registered clustering analysis (not performed).")
    else:
        story.append(P("PCA was skipped or under-powered because too few rows had jointly complete nutrient fields.", S["Body"]))

    story.append(P("9. Comparison with the Reference Paper", S["H1"]))
    story.append(P("Comparison with Universal Statistical Laws Governing Culinary Design. The paper is a methodological reference. CocktailDB is not required to match its exponents.", S["Body"]))
    cmp_rows = [
        ["Phenomenon", "Paper", "This dataset", "Method", "Evidence", "Interpretation"],
        ["Zipf", "f(r)~r^{-α}, α_global≈1.53; cuisine mean≈1.39; Clauset MLE on frequencies; LR vs log-normal/exponential",
         f"OLS α≈{fmt(alpha,2)} on r=5–{Z['primary_range']['rmax']}; Clauset α_freq≈{fmt(cl.get('alpha_freq_dist'),2)}, xmin={fmt(cl.get('xmin'),1)}",
         "Rank–frequency OLS + Clauset MLE",
         "Heavy tail yes; perfect power law not assumed",
         "Partially consistent: Zipf-like reuse in a smaller drink vocabulary"],
        ["Heaps", "V(R)~R^β, β≈0.56 (100 shuffles; methods also mention 10 for error bars)",
         f"β≈{fmt(beta,2)} (100 shuffles; 95% [{fmt(beta_ci[0],2)}, {fmt(beta_ci[1],2)}])",
         "Permutation + log–log OLS",
         f"mean R²={fmt(Hs['r2_mean'],3)}",
         "Consistent in sign (sublinear); similar magnitude is coincidental unless replicated on other drink corpora"],
        ["Menzerath–Altmann", "y(L)=a L^b e^{cL}; a=13.16,b=−0.26,c=−0.019; R²=0.99; min L≈13",
         f"ρ(L,y)={fmt(ma_sp,2)}; binned R²={fmt(ma_fit.get('r2'),2)}; L median={M['standard']['L_summary']['median']}",
         "Information s_i=−log p(i); NLS",
         "Short L range",
         "Different / weakly testable at the paper’s length scale"],
        ["Nutrient distributions", "Log-normal macros; mean KS 0.073 vs worse alternatives",
         f"Best KS by nutrient: {best_gof_txt}; incomplete coverage",
         "KS on x>0",
         "Nutrient n much smaller; serving unknown",
         "Partially testable; not a reproduction of meal log-normality"],
        ["Ingredient diversity", "19,019 unique ingredients; 1.15M mentions",
         f"{n_ing:,} standard unique; hapax={100*hapax:.1f}%",
         "Normalized tokens",
         "Smaller closed bar vocabulary",
         "Consistent with constrained vocabulary, different scale"],
        ["Recipe complexity", "Unimodal 8–12 ingredients; mean ~10; ~9 steps",
         f"median L={fmt(E['ingredient_count'].get('median'),0)}; mean={fmt(E['ingredient_count'].get('mean'),1)}; no steps",
         "Unique ingredient count",
         "No technique/step data",
         "Different: cocktails are shorter; steps not testable"],
    ]
    story.append(table(wrap_cells(cmp_rows, S), [22 * mm, 32 * mm, 32 * mm, 22 * mm, 22 * mm, 28 * mm]))
    story.append(Spacer(1, 4 * mm))

    story.append(P("10. Major Findings", S["H1"]))
    for i, fnd in enumerate(findings, 1):
        story.append(P(f"{i}. {fnd}", S["Body"]))

    story.append(P("11. Limitations", S["H1"]))
    lims = [
        "Missing values are extensive and structured; every analysis reports its own n.",
        "Cuisine is too sparse and semantically inconsistent (Cocktail vs American vs Vegan) for cuisine-level laws.",
        "Category incompleteness (about 59% missing) blocks globally representative category inference.",
        "Nutrient fields mix compact and colon formats; units were harmonized only where the text supported it.",
        "Ingredient normalization is partly subjective; sensitivity across four levels is provided but residual quantity/brand strings remain.",
        "The file likely concatenates heterogeneous sources (rating sites, recipe blogs, nutrition-labelled pages).",
        "Duplicate names may be variants or competing scrapes; only exact row and Name+Ingredients clones were dropped.",
        "Sampling bias: web cocktails over-represent English-language, Instagram-era, and database-popular drinks.",
        "Votes measure attention, not quality.",
        "Ratings with few votes are unstable and piled at 5.",
        "Observational correlations are not causal.",
        "Cocktail-specific composition may not generalize to global cuisine—the paper’s claim domain.",
        f"Corpus size ({n_corp:,} frequency recipes) is an order of magnitude below 118,083.",
        "No reliable geographic or cultural metadata.",
        "Prep times and nutrients may mix servings, infusions, and panel-generator artifacts; extremes were investigated, not auto-deleted.",
    ]
    for i, t in enumerate(lims, 1):
        story.append(P(f"{i}. {t}", S["Body"]))

    story.append(P("12. Future Work", S["H1"]))
    story.append(P("A cocktail-specific NER pass would align the corpus more closely with the paper’s structured entities. Linking drinks to flavor-compound data would test whether co-occurrence clusters match chemistry. Serving-size standardization is required before nutrient log-normality can be compared to packaged-food or RecipeDB results. Larger multilingual bar corpora would show whether β and α are drink-domain constants. Historical menus could separate traditional formulas from modern riffs.", S["Body"]))

    story.append(P("13. Conclusion", S["H1"]))
    story.append(P(
        f"CocktailDB supports the paper’s high-level claim that culinary compositions reuse a core vocabulary and accumulate novelty sublinearly: Zipf-like rank–frequency structure and Heaps β ≈ {fmt(beta,2)} are visible after careful normalization. It does not support a blanket transfer of the global Menzerath–Altmann minimum at L≈13, cuisine-universal exponents, technique scaling, or fully log-normal meal macronutrients. The honest result is mixed—and that is the scientifically relevant one.",
        S["Body"],
    ))

    story.append(P("References", S["H1"]))
    refs = [
        "Bagler, G. et al. Universal statistical laws governing culinary design. arXiv:2604.28021v1 (2026).",
        "Clauset, A., Shalizi, C. R. & Newman, M. E. J. Power-law distributions in empirical data. SIAM Rev. 51 (2009).",
        "Alstott, J., Bullmore, E. & Plenz, D. powerlaw: A Python package for analysis of heavy-tailed distributions. PLoS One 9, e85777 (2014).",
        "Altmann, G. Prolegomena to Menzerath’s law. Glottometrika 2, 1–10 (1980).",
        "Menichetti, G. & Barabási, A.-L. Nutrient concentrations in food display universal behaviour. Nat. Food 3, 375–382 (2022).",
        "Ahn, Y.-Y. et al. Flavor network and the principles of food pairing. Sci. Rep. 1, 196 (2011).",
        "Newman, M. E. J. Power laws, Pareto distributions and Zipf’s law. Contemp. Phys. 46, 323–351 (2005).",
        "Egghe, L. Untangling Herdan’s law and Heaps’ law. J. Am. Soc. Inf. Sci. Technol. 58, 702–709 (2007).",
    ]
    for r in refs:
        story.append(P(r, S["Caption"]))

    story.append(P("Appendix", S["H1"]))
    story.append(P("A. Reproducibility. Run python scripts/run_all.py from eda_project/. Numerical results live in tables/json/. Figures are written to figures/ as PNG and PDF. This report reads those files and does not hard-code exponents.", S["Body"]))
    story.append(P("B. Duplicate policy. Exact rows: remove extras (no information). Name+Ingredients clones: remove extras for frequency (avoid double-counting the same formula). Same name, different ingredients: keep (variants).", S["Body"]))
    story.append(P("C. Paper Methods notes used here. Ingredient frequency = recipe incidence; Zipf via rank–frequency plus Clauset MLE on frequencies with xmin by KS; Heaps V(R)=K R^β by log–log OLS on permutations; MA y(L)=a L^b exp(cL) by nonlinear least squares; nutrients: log transform of positives, log-skewness, KS versus log-normal/gamma/Weibull/Gaussian/exponential.", S["Body"]))
    story.append(P(f"D. Frequency corpus size = {n_corp:,}. Raw rows = {n:,}. Unique names = {n_names:,}. Unrated zeros = {C['n_unrated_zero_stars']}.", S["Body"]))

    REPORT.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Statistical Regularities in Cocktail Recipes",
        author="CocktailDB EDA pipeline",
    )
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    # copy to workspace root
    OUT_ROOT.write_bytes(OUT.read_bytes())
    print("wrote", OUT, "and", OUT_ROOT)


if __name__ == "__main__":
    main()
