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
