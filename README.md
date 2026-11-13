# Python-Based Business Data Analysis & Automated Reporting System

A modular Python application that ingests business sales data (CSV/Excel), validates and cleans it, computes business KPIs, and produces interactive dashboards plus downloadable Excel and PDF reports.

**Status:** under development (Milestone 1: environment setup).

## Requirements

- Python 3.12
- Git

## Setup (Windows, PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python verify_environment.py
```

## Dataset

UCI Online Retail dataset: https://archive.ics.uci.edu/dataset/352/online+retail
Place the downloaded file in `data/raw/` (not committed to Git).

More documentation (business rules, architecture, usage) will be added as the project progresses.

## BUSINESS_RULES

This section is the single source of truth for how the dataset is interpreted. Every rule is backed by the inspection of `Online Retail.xlsx` (541,909 rows x 8 columns, 2010-12-01 to 2011-12-09, 38 countries). Code must follow these rules; changing one requires an explicit decision recorded in `DEVELOPMENT_LOG.md`.

### Dataset facts

- Columns: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`.
- Missing `Description`: 1,454 rows. Missing `CustomerID`: 135,080 rows (about 25%). Exact duplicate rows: 5,268.
- `InvoiceNo` starting with `C`: 9,288 rows, all with negative `Quantity`.
- 1,336 non-`C` rows have `Quantity <= 0`; all have `UnitPrice = 0` and no `CustomerID`.
- 1,179 rows have `UnitPrice = 0` with `Quantity > 0`.
- 2 rows have a negative `UnitPrice` (invoices `A563186`, `A563187`, code `B`, "Adjust bad debt").
- No invoice has more than one country or more than one `CustomerID` (blank IDs not counted in this check).

### What the dataset does not contain

- **No product category column.** Contribution is reported by product (`StockCode`) only. Categories are never inferred from descriptions.
- **No refund or payment events.** Returns exist only as cancelled invoices, so they are called *returns*, not refunds.
- **No currency is stated.** Amounts are labelled "currency units".
- **No link between a return and its original sale.** Returns are counted in the period of the cancellation.

### Rules

| # | Rule | Treatment |
|---|---|---|
| R1 | Sale row | `InvoiceNo` not starting with `C`, `Quantity > 0`, `UnitPrice > 0`, and a product `StockCode` (see R5). |
| R2 | Return row | `InvoiceNo` starts with `C` (`Quantity < 0`). Reported as returns/cancellations. |
| R3 | Non-sale adjustments | Non-`C` rows with `Quantity <= 0`, and negative-price rows. Kept in the audit trail with a flag; excluded from all KPIs. |
| R4 | Zero-price sales | `UnitPrice = 0` with `Quantity > 0`. Excluded from KPIs; kept in cleaned data with a flag. |
| R5 | Non-product codes | `POST`, `DOT`, `M`, `D`, `S`, `BANK CHARGES`, `AMAZONFEE`, `CRUK`, `B`, `C2` (carriage), and any code starting with `GIFT_` (gift vouchers); case-insensitive, so `m` is included. Flagged `is_product = False`, excluded from product analytics, and reported on a separate shipping/fees line. Codes containing digits were reviewed in Milestone 5; only `C2` and `GIFT_*` were added. |
| R6 | Missing `CustomerID` | Rows are kept for revenue, orders, product and country analysis. Excluded only from customer-level analysis; the count is reported. |
| R7 | Exact duplicates | Removed, with row count and revenue impact in the audit trail. A settings switch will allow keeping them. Caveat: an identical repeated line could be a genuine double entry. |
| R8 | Missing `Description` | Kept and shown as "(no description)". The product key is `StockCode`. |
| R9 | Metrics | `LineTotal = Quantity x UnitPrice`. Gross sales = sum of `LineTotal` over R1 rows. Returns value = sum of `LineTotal` over R2 rows (negative). Net revenue = gross sales + returns value. Orders = distinct `InvoiceNo` among R1 rows (never counted per line). |
| R10 | Returns period | Returns are attributed to the month of the cancellation invoice, not the original sale. |

### Standardisation

- `InvoiceNo`, `StockCode` and `CustomerID` are handled as text, with whitespace stripped; `StockCode` is upper-cased. Every change is counted in the audit trail.
- `Country` values are kept as supplied. `Unspecified` and `European Community` are not real countries, and `EIRE`/`RSA` are non-standard labels; none are merged or renamed.
