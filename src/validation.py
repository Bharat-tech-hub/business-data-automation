"""Data-quality validation for the raw sales DataFrame.

Counts problems and classifies them as blocking, warning or info. It never
modifies the data; cleaning is a separate step. Rule codes (R1-R10) refer to
BUSINESS_RULES in the README.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from src.logger import get_logger
from src.schema import (
    CANCELLATION_PREFIX,
    NON_PRODUCT_STOCK_CODES,
    REQUIRED_COLUMNS,
    TEXT_ID_COLUMNS,
)

logger = get_logger("validation")

# Share of unusable values above which a critical column blocks the analysis.
BLOCKING_THRESHOLD: float = 0.05

# Columns whose missing or unparseable values are reported as "unusable".
_CRITICAL_COLUMNS: tuple[str, ...] = ("InvoiceDate", "Quantity", "UnitPrice")


class Severity(str, Enum):
    """How serious a finding is."""

    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


_RANK = {Severity.BLOCKING: 0, Severity.WARNING: 1, Severity.INFO: 2}


@dataclass(frozen=True)
class Finding:
    """One data-quality observation."""

    code: str
    severity: Severity
    message: str
    count: int
    share: float | None = None  # fraction of rows; None when not row-based


@dataclass
class ValidationReport:
    """Result of validating a dataset."""

    total_rows: int
    sale_rows: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def blocking_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.BLOCKING]

    @property
    def warning_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARNING]

    @property
    def has_blocking_errors(self) -> bool:
        return bool(self.blocking_findings)

    def get(self, code: str) -> Finding | None:
        """Return the finding with this code, or None."""
        return next((f for f in self.findings if f.code == code), None)

    def to_frame(self) -> pd.DataFrame:
        """Findings as a table for display."""
        rows = [
            {
                "severity": f.severity.value,
                "code": f.code,
                "count": f.count,
                "share_pct": None if f.share is None else round(f.share * 100, 2),
                "message": f.message,
            }
            for f in self.findings
        ]
        return pd.DataFrame(rows, columns=["severity", "code", "count", "share_pct", "message"])


def _is_missing(series: pd.Series) -> pd.Series:
    """True where a value is null, or (for text columns) empty or whitespace."""
    na = series.isna()
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
        return na
    blank = series.where(~na, "").astype(str).str.strip().eq("")
    return na | blank


def _as_text(series: pd.Series) -> pd.Series:
    """Stripped text version of a column; missing values become empty strings."""
    return series.astype(str).str.strip().where(series.notna(), "")


def _minority_type_count(series: pd.Series) -> int:
    """Number of non-null values whose Python type is not the most common one."""
    values = series.dropna()
    if values.empty:
        return 0
    counts = values.map(type).value_counts()
    return int(counts.iloc[1:].sum()) if len(counts) > 1 else 0


def _add(
    findings: list[Finding],
    code: str,
    severity: Severity,
    message: str,
    count: int,
    total: int,
) -> None:
    """Append a finding only when something was actually found."""
    if count > 0:
        findings.append(Finding(code, severity, message, int(count), count / total))


def validate(df: pd.DataFrame) -> ValidationReport:
    """Validate a raw DataFrame and return a report. The input is not modified.

    Raises:
        ValueError: If required columns are missing (ingestion normally prevents this).
    """
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required column(s): {', '.join(missing_columns)}")

    total = len(df)
    if total == 0:
        empty = Finding("empty_dataset", Severity.BLOCKING, "The dataset has no rows.", 0)
        return ValidationReport(total_rows=0, sale_rows=0, findings=[empty])

    findings: list[Finding] = []

    # Duplicate headers: pandas renames repeats to "Name.1", "Name.2", ...
    column_set = {str(c) for c in df.columns}
    duplicated_headers = 0
    for col in df.columns:
        match = re.fullmatch(r"(.+)\.\d+", str(col))
        if match and match.group(1) in column_set:
            duplicated_headers += 1
    if duplicated_headers:
        findings.append(
            Finding(
                "duplicate_headers",
                Severity.WARNING,
                "Repeated column headers were found (renamed with a numeric suffix).",
                duplicated_headers,
            )
        )

    # Parse the critical columns without changing the data.
    dates = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    qty = pd.to_numeric(df["Quantity"], errors="coerce")
    price = pd.to_numeric(df["UnitPrice"], errors="coerce")
    unusable = {
        "InvoiceDate": int(dates.isna().sum()),
        "Quantity": int(qty.isna().sum()),
        "UnitPrice": int(price.isna().sum()),
    }
    labels = {
        "InvoiceDate": "not a valid date",
        "Quantity": "not a valid number",
        "UnitPrice": "not a valid number",
    }
    for col in _CRITICAL_COLUMNS:
        count = unusable[col]
        if count == 0:
            continue
        share = count / total
        severity = Severity.BLOCKING if share > BLOCKING_THRESHOLD else Severity.WARNING
        findings.append(
            Finding(
                f"unusable_{col.lower()}",
                severity,
                f"{col} is missing or {labels[col]} in {count:,} rows "
                f"({share:.1%}); blocking above {BLOCKING_THRESHOLD:.0%}.",
                count,
                share,
            )
        )

    # Missing values in the other columns.
    for col in REQUIRED_COLUMNS:
        if col in _CRITICAL_COLUMNS:
            continue
        _add(
            findings,
            f"missing_{col.lower()}",
            Severity.WARNING,
            f"{col} is missing or blank.",
            int(_is_missing(df[col]).sum()),
            total,
        )

    _add(
        findings,
        "duplicate_rows",
        Severity.WARNING,
        "Exact duplicate rows (rule R7: removed during cleaning).",
        int(df.duplicated().sum()),
        total,
    )

    # Business-rule categories.
    invoice = _as_text(df["InvoiceNo"])
    stock = _as_text(df["StockCode"]).str.upper()
    is_cancel = invoice.str.startswith(CANCELLATION_PREFIX).astype(bool)
    is_non_product = stock.isin(list(NON_PRODUCT_STOCK_CODES))

    _add(
        findings,
        "cancelled_rows",
        Severity.INFO,
        "Cancelled invoices, treated as returns (rule R2).",
        int((is_cancel).sum()),
        total,
    )
    _add(
        findings,
        "nonpositive_quantity_non_cancelled",
        Severity.WARNING,
        "Non-cancelled rows with quantity <= 0, treated as adjustments (rule R3).",
        int((~is_cancel & (qty <= 0)).sum()),
        total,
    )
    _add(
        findings,
        "zero_price_positive_quantity",
        Severity.WARNING,
        "Rows with unit price 0 and positive quantity (rule R4: excluded from KPIs).",
        int(((price == 0) & (qty > 0)).sum()),
        total,
    )
    _add(
        findings,
        "negative_price",
        Severity.WARNING,
        "Rows with a negative unit price (rule R3).",
        int((price < 0).sum()),
        total,
    )
    _add(
        findings,
        "non_product_codes",
        Severity.INFO,
        "Rows with fee, postage or adjustment stock codes (rule R5).",
        int(is_non_product.sum()),
        total,
    )

    # Mixed-type identifier columns (typical for XLSX files).
    for col in TEXT_ID_COLUMNS:
        count = _minority_type_count(df[col])
        if count:
            findings.append(
                Finding(
                    f"mixed_type_{col.lower()}",
                    Severity.INFO,
                    f"{col} mixes value types; it will be converted to text during cleaning.",
                    count,
                    count / total,
                )
            )

    # Rule R1: rows that can count as sales.
    sale_mask = ~is_cancel & (qty > 0) & (price > 0) & ~is_non_product
    sale_rows = int(sale_mask.sum())
    if sale_rows == 0:
        findings.append(
            Finding(
                "no_sale_rows",
                Severity.BLOCKING,
                "No rows qualify as sales under rule R1; nothing can be analysed.",
                0,
            )
        )

    findings.sort(key=lambda f: _RANK[f.severity])
    report = ValidationReport(total_rows=total, sale_rows=sale_rows, findings=findings)
    logger.info(
        "Validated %d rows: %d blocking, %d warning finding(s), %d sale rows",
        total,
        len(report.blocking_findings),
        len(report.warning_findings),
        sale_rows,
    )
    return report
