"""Dataset schema constants shared by ingestion, validation and cleaning.

These reflect the inspected UCI Online Retail file (see BUSINESS_RULES in the
README). Business rule R5 (non-product codes) lives here as data, not logic.
"""

from __future__ import annotations

REQUIRED_COLUMNS: tuple[str, ...] = (
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
)

# Identifier columns that must be treated as text, never as numbers.
TEXT_ID_COLUMNS: tuple[str, ...] = ("InvoiceNo", "StockCode", "CustomerID")

# Cancelled invoices (returns) start with this prefix (rule R2).
CANCELLATION_PREFIX: str = "C"

# Stock codes that are fees, postage or adjustments, not products (rule R5).
# Stored upper-case; compare against upper-cased StockCode values.
NON_PRODUCT_STOCK_CODES: frozenset[str] = frozenset(
    {"POST", "DOT", "M", "D", "S", "BANK CHARGES", "AMAZONFEE", "CRUK", "B"}
)
