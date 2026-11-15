# Development Log

## Milestone 10, step 10b: PDF report (complete)

**Date:** 2026-11-15

### Completed
- `src/reporting.py`: `build_pdf(df, ctx)` (A4, reportlab): title, report date, filters, KPI table, computed observations, notes, four static charts, top-10 products and countries tables, and a Data quality section when validation/cleaning reports are supplied. Text is XML-escaped.
- `src/visualization.py`: comma-formatted money axes on static charts (commit 9afa43a).
- `tests/test_pdf.py`: 6 structural tests. Full suite: 147 passed.
- Real-file PDF reviewed by eye: KPIs, observations, charts, tables and data-quality tables match earlier runs.

### Decisions
- A4 page size (approved "defaults").
- No PDF text reader (`pypdf`) was added, so tests check structure, not the text of each number.

### Known limitations
- The "Data quality" heading can be separated from its tables across a page break.
- Whether the title is clipped on page 1 was not confirmed (screenshot crop).
- Products, Countries and Customers Excel sheets were not reviewed by eye.

### Pending
- Milestone 11: Streamlit dashboard (including the upload size cap).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 10, step 10a: Excel report (complete)

**Date:** 2026-11-15

### Completed
- `src/reporting.py`: `ReportContext`, `describe_filter`, `kpi_rows`, `build_excel` (sheets: Summary, Monthly with a native column chart, Products, Countries, Customers, Data quality), `save_report` (sanitised name, .xlsx/.pdf only, writes to `reports/`).
- `tests/test_reporting.py`: 10 tests that read the generated workbook back and compare with hand-calculated KPIs. Full suite: 141 passed.
- Real-file report reviewed in Excel: Summary KPIs, Monthly (13 months, chart) and Data quality (10 findings, 6 audit lines) match earlier runs. Fixed: wrapped long text on Summary; widened the `code` column on Data quality (not re-checked by eye).

### Decisions
- Module built in three small pastes because large terminal pastes were doubling.
- Chart presence is not asserted in tests (openpyxl does not reliably load charts); checked by eye.

### Known limitations
- Products, Countries and Customers sheets were not reviewed by eye.
- The Excel monthly chart does not colour the partial month; the `partial` column shows it.
- Summary rows are taller than needed.

### Pending
- Step 10b: PDF report and axis number formatting in `src/visualization.py`.
- Streamlit upload cap (Milestone 11).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 9: Visualization layer (complete)

**Date:** 2026-11-14

### Completed
- `src/visualization.py`: six static (Matplotlib `Figure`) and five interactive (Plotly) chart functions. They cover monthly revenue with partial months in a lighter colour, top products, country revenue (optionally excluding the largest market), weekday/hour, customer spend (static only, log scale) and RFM. All accept a `KpiFilter` and return a "No data for the selected filters" figure when empty.
- `tests/test_visualization.py`: 11 tests. Full suite: 131 passed.
- All six real-file previews reviewed by eye: partial month is lighter, labels readable, Saturday empty, country chart excludes the UK, distributions consistent with the notebook figures.

### Decisions
- One module with `static_*` and `interactive_*` functions (approved "defaults").
- Static figures use `matplotlib.figure.Figure`, not `pyplot`.
- PDF charts will use the static functions; no `kaleido` was added.

### Known limitations
- Tests check structure, not appearance.
- Axes use scientific notation (1e6) and unformatted numbers; comma formatting is planned for Milestone 10.
- Customer spend has no interactive version yet.

### Pending
- Milestone 10: Excel and PDF reporting (including axis number formatting).
- Streamlit upload cap (Milestone 11).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 8: Advanced analytics (complete)

**Date:** 2026-11-14

### Completed
- `src/analytics.py`: `product_performance`, `country_performance`, `rfm_table`, `spend_concentration`, `monthly_trend`, `quarterly_trend`, `observations`. All accept an optional `KpiFilter`.
- `tests/test_analytics.py`: 9 tests on a hand-built frame. Full suite: 120 passed.
- Real-file run reproduces the notebook: concentration 61.4%, 4,334 customers, same observation sentences. December 2011, 2010Q4 and 2011Q4 are flagged partial and excluded from growth.

### Decisions
- Partial periods are flagged, shown, and excluded from growth rates (approved "defaults"). Partial = data starts after the period's first day or ends before its last day, computed from the data.
- RFM recency uses whole calendar days against the day after the last invoice.

### Bugs found by tests
- Test fixture used stock code "B", which is an R5 non-product code; the rule worked as designed. Fixture changed to a real product code.
- Recency leaked time of day into day counts (floor of a fractional span). Fixed by normalising the last order date
@'
# Development Log

## Milestone 8: Advanced analytics (complete)

**Date:** 2026-11-14

### Completed
- `src/analytics.py`: `product_performance`, `country_performance`, `rfm_table`, `spend_concentration`, `monthly_trend`, `quarterly_trend`, `observations`. All accept an optional `KpiFilter`.
- `tests/test_analytics.py`: 9 tests on a hand-built frame. Full suite: 120 passed.
- Real-file run reproduces the notebook: concentration 61.4%, 4,334 customers, same observation sentences. December 2011, 2010Q4 and 2011Q4 are flagged partial and excluded from growth.

### Decisions
- Partial periods are flagged, shown, and excluded from growth rates (approved "defaults"). Partial = data starts after the period's first day or ends before its last day, computed from the data.
- RFM recency uses whole calendar days against the day after the last invoice.

### Bugs found by tests
- Test fixture used stock code "B", which is an R5 non-product code; the rule worked as designed. Fixture changed to a real product code.
- Recency leaked time of day into day counts (floor of a fractional span). Fixed by normalising the last order date to midnight.

### Known limitations
- The first months of the monthly table were not reviewed by me; the reasons for month-to-month swings are not explained by the data.
- Q4 2010 is partial only because the data starts on 2010-12-01.

### Pending
- Milestone 9: visualization layer.
- Streamlit upload cap (Milestone 11).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 7: KPI engine (complete)

**Date:** 2026-11-14

### Completed
- `src/kpis.py`: `KpiFilter`, `apply_filter`, `compute_kpis` (-> `KpiSummary`), `revenue_by_country`, `revenue_by_product` (with cumulative share; no categories exist), `monthly_revenue`, `customer_frequency`, `repeat_customer_share`.
- `tests/test_kpis.py`: 11 tests on a hand-built frame. Full suite: 111 passed.
- Real-file run reproduces the notebook: gross 10,247,219.32; returns -893,979.73; net 9,353,239.59; 19,773 orders; AOV 518.24; return rate 8.72%; fees 394,891.48; 4,334 customers, 65.3% repeat. New: 5,561,387 units; average selling price 1.84.

### Decisions
- Average selling price = gross sales / units sold (approved "defaults"). Recorded in the README.
- Filters live in one `apply_filter` used by every function.

### Known limitations
- Units total and ASP were not cross-checked independently.
- Return rate is a ratio of totals (R10).

### Pending
- Milestone 8: advanced analytics.
- Streamlit upload cap (Milestone 11).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 6: Exploratory data analysis notebook (complete)

**Date:** 2026-11-14

### Completed
- `notebooks/01_eda.ipynb` (27 cells, committed with outputs cleared): load, validate and clean the real file; sales distributions; products; countries; time patterns; customers; and a cell that generates its observations from the data.
- Verified on the real file (all computed, none hand-written): 522,540 sale rows over 19,773 invoices; gross sales 10,247,219.32; returns -893,979.73 (8.7% of gross); net revenue 9,353,239.59; average order value 518.24; 3,799 products sold, 816 (21.5%) making up 80% of product revenue; shipping/fees/vouchers 394,891.48 reported separately; 38 countries, UK 85.1%; 4,334 identified customers, 65.3% with more than one order, top 10% of customers = 61.4% of customer spend; 25.1% of sale rows have no CustomerID; no sales on Saturdays.
- Charts use Matplotlib/Seaborn only.

### Decisions
- Notebook generated by temporary scripts (deleted), because long pastes into the terminal were unreliable.
- Outputs are not committed (keeps Git small, avoids leaking paths).

### Known limitations
- The section 5 monthly table and peak-hour line were not reviewed by me; they run in the notebook but are not interpreted here.
- Returns are attributed to the cancellation month and are not linked to original sales (R10), so the 8.7% is a ratio of totals.
- These are exploratory numbers; the formal KPI definitions come in Milestone 7.

### Pending
- Milestone 7: KPI engine.
- Streamlit upload cap (Milestone 11).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 6 (step 6a): ipykernel added (complete)

**Date:** 2026-11-13

### Completed
- Approved by you and installed: `ipykernel` 7.4.0 (IPython 9.18.1). Justification: lets VS Code run `.ipynb` notebooks with the project's `.venv`. No `jupyter`, `jupyterlab` or `notebook` was installed, so no web server is added.
- `pip check`: no broken requirements. `verify_environment.py`: ten OK. Tests: 100 passed.
- `requirements.txt` re-pinned: 51 -> 73 lines, 22 insertions, no existing version changed.

### Pending
- Step 6b: generate `notebooks/01_eda.ipynb` and check the kernel in VS Code.
- Streamlit upload cap (Milestone 11).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 5: Data cleaning and audit trail (complete)

**Date:** 2026-11-13

### Completed
- `src/cleaning.py`: `clean(df)` returns `(cleaned, CleaningReport)`. Steps: strip whitespace, convert IDs to text (`CustomerID` as integer text), upper-case `StockCode`, parse date/number columns (drop unusable rows), fill missing descriptions (R8), remove exact duplicates (R7, constant `REMOVE_DUPLICATES`), add `is_cancelled`, `is_product`, `is_sale`, `has_customer`, `LineTotal`, `InvoiceMonth`. Also `build_product_names()` and `save_processed()`. The input is never modified.
- `tests/test_cleaning.py`: 15 tests. Full suite: 100 passed.
- Real-file run: 541,909 -> 536,641 rows; whitespace cells 113,452; StockCode upper-cased 1,977; descriptions filled 1,454; duplicates removed 5,268; unusable rows 0; 522,540 sale rows.

### Decisions
- Product name = most frequent stripped description per StockCode, as a separate lookup; rows are not rewritten.
- Missing CustomerID is stored as an empty string with `has_customer = False`.

### Known limitations
- `save_processed()` exists but nothing calls it yet; the dashboard and `run.py` will.
- My test-count predictions were off by one again (16 vs 15); counts above are from real runs.

### Pending
- Milestone 6: exploratory data analysis (notebook).
- Streamlit upload cap (Milestone 11).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 5 (step 5b): Rule R5 extended (complete)

**Date:** 2026-11-13

### Completed
- Four read-only inspections of `Online Retail.xlsx` settled the cleaning rules.
- `src/schema.py`: R5 now includes `C2` (carriage) and the `GIFT_` prefix (vouchers), via one shared helper `non_product_mask()` so validation and cleaning cannot disagree.
- `src/validation.py` now uses `non_product_mask()`. README R5 row updated.
- Tests: 85 passed (3 new). Real file: non-product rows 2,946; candidate sale rows 527,761; not blocking.

### Findings for step 5c (cleaning)
- `StockCode`: 487,036 ints and 54,873 strings; no float artefacts. 1,977 rows have lowercase letters; 112 codes have more than one spelling. Upper-casing merges them.
- `CustomerID`: no non-integer values, so it converts to integer text safely.
- `Description`: 113,452 rows (about 21%) carry leading/trailing whitespace; one description is a stray number (`20713`). Strip, convert to text, keep case.
- Up to 8 description variants per code. Product-name rule: most frequent stripped description per `StockCode`, kept as a separate lookup; rows are not rewritten.
- Near-duplicates (5,270) vs exact (5,268): R7 stays on exact duplicates, measured after normalisation, with both counts logged.

### Decisions
- R7 "keep duplicates" switch is a module constant in the cleaning module; `config/settings.py` unchanged.

### Pending
- Step 5c: `src/cleaning.py`, audit trail, tests, and tidying the README R5 sentence about digit codes.
- Streamlit upload cap (Milestone 11).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 4: Data validation (complete)

**Date:** 2026-11-13

### Completed
- `src/validation.py`: `validate(df)` returns a `ValidationReport` of `Finding`s classified as blocking, warning or info. It checks missing values, exact duplicates, unusable dates/quantities/prices, duplicate headers, mixed-type ID columns, and the BUSINESS_RULES categories (R2, R3, R4, R5, R6, R8). It never modifies the input.
- `tests/test_validation.py`: 24 tests on 20-row hand-built fixtures. Full suite: 82 passed, no warnings.
- Real-file check (`Online Retail.xlsx`, 541,909 rows): not blocking; 527,933 candidate sale rows; counts match the inspection (duplicates 5,268; missing CustomerID 135,080; missing Description 1,454; cancelled 9,288; non-cancelled non-positive quantity 1,336; zero price with positive quantity 1,179; negative price 2; non-product codes 2,768).

### Decisions
- Blocking threshold is 5% (constant `BLOCKING_THRESHOLD` in `src/validation.py`); `config/settings.py` unchanged. Exactly 5% is a warning, above 5% blocks.
- Missing or unparseable `InvoiceDate`, `Quantity`, `UnitPrice` are reported together as "unusable_*".

### Findings for Milestone 5
- `StockCode` is mixed-type in 54,873 rows (10.1%) and `InvoiceNo` in 9,291 rows. Cleaning must convert both to text without float artefacts (e.g. `22423.0`).
- `CustomerID` is float64 because of nulls; it must become text like `17850`, not `17850.0`.
- Still to do: check for non-product stock codes that contain digits (R5 note).

### Pending
- Milestone 5: data cleaning and audit trail.
- Streamlit upload cap (Milestone 11).
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 3: Data ingestion (complete)

**Date:** 2026-11-13

### Completed
- `src/ingestion.py`: safe CSV/XLSX loading with filename sanitising, extension, size, content and required-column checks, a zip-bomb guard, UTF-8 with Latin-1 fallback, and custom exceptions (`IngestionError` and five subclasses). Returns `(DataFrame, IngestionResult)`.
- `tests/test_ingestion.py`: 24 tests using small hand-built fixtures. Full suite: 58 passed, no warnings.
- Real-file check: `Online Retail.xlsx` loads as 541,909 x 8 with no warnings.
- Fixed a pandas deprecation (`ExcelFile.parse`) by reading the sheet with `pd.read_excel`.

### Decisions
- Ingestion does not parse types or dates; Milestone 4 validation counts bad values instead of crashing the load.
- Business rules R1-R10 remain the source of truth (README, BUSINESS_RULES).

### Known limitations
- Duplicate CSV headers are renamed by pandas and are not flagged yet; Milestone 4 will check them.
- The size limit is checked on bytes already in memory; Streamlit's own upload cap should also be set in Milestone 11.
- My earlier test-count predictions were off by one (23 vs 24); counts above are from real runs.

### Pending
- Milestone 4: data validation.
- Milestone 5: check for non-product stock codes that contain digits.
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 3: Data ingestion (in progress)

**Date started:** 2026-11-12

### Completed so far
- Dataset `Online Retail.xlsx` (22.6 MB, 541,909 x 8) placed in `data/raw/` (git-ignored) and inspected twice, read-only.
- Business rules R1-R10 approved and recorded in the README under BUSINESS_RULES (source of truth).
- `src/schema.py`: required columns, text ID columns, cancellation prefix, non-product stock codes. `tests/test_schema.py`: 5 tests.

### Decisions
- `required_columns` is NOT added to `Settings`; it lives in `src/schema.py` (Milestone 2 code unchanged).
- Rules R4, R5, R7 approved: zero-price rows excluded, fees on a separate line, exact duplicates removed (with a settings switch to keep them).
- Amounts are labelled "currency units" because the dataset states no currency.
- No product categories: contribution is by product only.

### Pending
- Step 3e: `src/ingestion.py` and tests.
- Milestone 5: check for non-product stock codes that contain digits.
- LICENSE decision (deferred; revisit before Milestone 13).

---

# Development Log

## Milestone 2: Configuration and logging foundation (complete)

**Date:** 2026-11-12

### Completed
- `config/settings.py`: frozen, validated `Settings` dataclass (paths, 50 MB upload limit, `.csv`/`.xlsx` allowed, logging options) plus `is_extension_allowed()`.
- `src/logger.py`: console and rotating-file logging, idempotent `setup_logging()`, `get_logger()`, `shutdown_logging()`.
- `tests/test_config.py` and `tests/test_logger.py`: 29 tests, all passing (Python 3.12.10, pytest 9.2.0).
- Manual check: a demo message appeared on the console and in `logs/app.log`; the log file is git-ignored.

### Decisions
- No `pytest.ini`; run tests with `python -m pytest`, not bare `pytest`.
- Plain Python settings module; no PyYAML.
- Upload limit defaults to 50 MB and is configurable.

### Pending
- LICENSE decision (deferred; revisit before Milestone 13).
- Dataset: download the UCI Online Retail file into `data/raw/` before Milestone 3.

---

# Development Log

## Milestone 1: Environment and Project Initialization (complete)

**Dates:** 2026-11-10 to 2026-11-12

### Completed
- Windows 11, PowerShell, VS Code.
- Python 3.12.10 virtual environment (`.venv`). Python 3.14.2 remains the system default; not used because of library wheel risk.
- Git 2.56.0.4 installed. pip upgraded to 26.3.
- Folder structure created per the project brief; `.gitkeep` placeholders added.
- `.gitignore` created.
- Libraries installed and import-verified: pandas 3.1.1, numpy 2.5.4, matplotlib 3.11.2, seaborn 0.13.2, plotly 7.1.0, streamlit 1.67.0, openpyxl 3.1.5, xlsxwriter 3.3.1, reportlab 5.1.0, pytest 9.2.0.
- `requirements.txt` pinned (51 lines, UTF-8) and confirmed with `pip install -r`.
- Git identity set (name "Bharat", GitHub no-reply email). "Keep my email private" and "Block command line pushes" are ON.
- First commit `59dcafc` pushed to https://github.com/Bharat-tech-hub/business-data-automation (public, branch `main`).

### Decisions
- Local root folder is `D:\Python-Business-Development` (local naming change from `business-data-automation/`); the GitHub repo uses the brief's name.
- No libraries outside the approved stack. Plotly charts stay in the dashboard; PDF charts use Matplotlib/Seaborn.
- `verify_environment.py` kept at the root as a temporary utility until Milestone 13.
- Personal scratch file `program.py` moved out of the repo to `D:\scratch`.

### Known issues (fixed)
- PowerShell execution policy blocked venv activation; set to RemoteSigned for the current user.
- `requirements.txt` was first frozen before verification and was re-frozen as UTF-8 afterwards.

### Pending
- LICENSE decision (skipped for now; the brief lists a LICENSE file, so revisit before Milestone 13).
- Dataset: download the UCI Online Retail file into `data/raw/` (needed at the start of Milestone 3; no schema or business rule is finalized before inspection output is reviewed).
