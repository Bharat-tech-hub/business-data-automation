"""Cleaning of the raw sales DataFrame under BUSINESS_RULES R1-R10.

Never modifies its input. Every change is recorded in a CleaningReport so the
result is auditable: what changed, how many rows or cells, and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.logger import get_logger
from src.schema import CANCELLATION_PREFIX, REQUIRED_COLUMNS, non_product_mask

logger = get_logger("cleaning")

# Rule R7: remove exact duplicate rows (after normalisation). Set False to keep them.
REMOVE_DUPLICATES: bool = True

NO_DESCRIPTION: str = "(no description)"

_TEXT_COLUMNS: tuple[str, ...] = ("InvoiceNo", "StockCode", "Description", "CustomerID", "Country")


@dataclass(frozen=True)
class AuditEntry:
    """One recorded cleaning operation."""

    step: str
    affected: int
    reason: str


@dataclass
class CleaningReport:
    """Audit trail of a cleaning run."""

    rows_in: int
    rows_out: int = 0
    entries: list[AuditEntry] = field(default_factory=list)

    def add(self, step: str, affected: int, reason: str) -> None:
        self.entries.append(AuditEntry(step, int(affected), reason))

    def get(self, step: str) -> AuditEntry | None:
        """Return the audit entry with this step name, or None."""
        return next((e for e in self.entries if e.step == step), None)

    def to_frame(self) -> pd.DataFrame:
        """Audit trail as a table for display or export."""
        return pd.DataFrame(
            [{"step": e.step, "affected": e.affected, "reason": e.reason} for e in self.entries],
            columns=["step", "affected", "reason"],
        )


def _to_text(series: pd.Series) -> pd.Series:
    """Convert to plain text; missing values become empty strings (object dtype)."""
    return series.map(lambda v: "" if pd.isna(v) else str(v)).astype(object)


def _customer_text(series: pd.Series) -> pd.Series:
    """CustomerID as integer text (17850, not 17850.0); missing becomes empty."""

    def convert(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        text = str(value).strip()
        if text.endswith(".0") and text[:-2].isdigit():
            return text[:-2]
        return text

    return series.map(convert).astype(object)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean a raw DataFrame and return ``(cleaned, report)``. The input is not modified.

    Raises:
        ValueError: If required columns are missing.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    report = CleaningReport(rows_in=len(df))
    out = df.loc[:, list(REQUIRED_COLUMNS)].copy()

    # 1-2. Text normalisation (counting cells that actually change).
    stripped_cells = 0
    for col in _TEXT_COLUMNS:
        before = _customer_text(out[col]) if col == "CustomerID" else _to_text(out[col])
        after = before.str.strip()
        stripped_cells += int((before != after).sum())
        out[col] = after
    report.add("strip_whitespace", stripped_cells, "Leading/trailing spaces removed from text cells.")

    upper = out["StockCode"].str.upper()
    report.add(
        "uppercase_stockcode",
        int((upper != out["StockCode"]).sum()),
        "StockCode upper-cased so spellings such as 84872a and 84872A merge.",
    )
    out["StockCode"] = upper

    # 3. Parse dates and numbers; drop rows where they are unusable.
    out["InvoiceDate"] = pd.to_datetime(out["InvoiceDate"], errors="coerce")
    out["Quantity"] = pd.to_numeric(out["Quantity"], errors="coerce")
    out["UnitPrice"] = pd.to_numeric(out["UnitPrice"], errors="coerce")
    unusable = out["InvoiceDate"].isna() | out["Quantity"].isna() | out["UnitPrice"].isna()
    report.add(
        "drop_unusable_rows",
        int(unusable.sum()),
        "Rows with an invalid or missing date, quantity or unit price were dropped.",
    )
    out = out.loc[~unusable].copy()

    # 4. Missing descriptions (R8).
    blank_desc = out["Description"].eq("")
    report.add(
        "fill_missing_description",
        int(blank_desc.sum()),
        f"Missing Description set to '{NO_DESCRIPTION}' (rule R8).",
    )
    out.loc[blank_desc, "Description"] = NO_DESCRIPTION

    # 5. Exact duplicates (R7), measured after normalisation.
    dup = out.duplicated()
    if REMOVE_DUPLICATES:
        report.add("remove_duplicates", int(dup.sum()), "Exact duplicate rows removed (rule R7).")
        out = out.loc[~dup].copy()
    else:
        report.add("remove_duplicates", 0, f"Kept {int(dup.sum())} duplicates (REMOVE_DUPLICATES is False).")

    # 6. Flags and derived columns.
    out["is_cancelled"] = out["InvoiceNo"].str.startswith(CANCELLATION_PREFIX)
    out["is_product"] = ~non_product_mask(out["StockCode"])
    out["is_sale"] = (
        ~out["is_cancelled"] & (out["Quantity"] > 0) & (out["UnitPrice"] > 0) & out["is_product"]
    )
    out["has_customer"] = out["CustomerID"].ne("")
    out["LineTotal"] = out["Quantity"] * out["UnitPrice"]
    out["InvoiceMonth"] = out["InvoiceDate"].dt.to_period("M").astype(str)

    out = out.reset_index(drop=True)
    report.rows_out = len(out)
    report.add("flags_added", len(out), "Added is_cancelled, is_product, is_sale, has_customer, LineTotal, InvoiceMonth.")
    logger.info("Cleaned %d -> %d rows (%d audit entries)", report.rows_in, report.rows_out, len(report.entries))
    return out, report


def build_product_names(cleaned: pd.DataFrame) -> pd.Series:
    """Most frequent description per StockCode (ties: alphabetical), ignoring blanks."""
    named = cleaned.loc[cleaned["Description"] != NO_DESCRIPTION, ["StockCode", "Description"]]
    counts = named.groupby(["StockCode", "Description"]).size().reset_index(name="n")
    counts = counts.sort_values(["StockCode", "n", "Description"], ascending=[True, False, True])
    return counts.drop_duplicates("StockCode").set_index("StockCode")["Description"]


def save_processed(cleaned: pd.DataFrame, path: str | Path) -> Path:
    """Write the cleaned data to a CSV file and return its path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(target, index=False, encoding="utf-8")
    logger.info("Saved cleaned data to %s", target.name)
    return target
