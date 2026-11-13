"""Dataset schema constants shared by ingestion, validation and cleaning.

These reflect the inspected UCI Online Retail file (see BUSINESS_RULES in the
README). Business rule R5 (non-product codes) lives here as data plus one
shared helper, so validation and cleaning can never disagree.
"""

from __future__ import annotations

import pandas as pd

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

# Stock codes that are fees, postage, carriage or adjustments, not products (rule R5).
# Stored upper-case; compare against upper-cased StockCode values.
NON_PRODUCT_STOCK_CODES: frozenset[str] = frozenset(
    {"POST", "DOT", "M", "D", "S", "BANK CHARGES", "AMAZONFEE", "CRUK", "B", "C2"}
)

# Stock-code prefixes that are not products, e.g. gift vouchers (rule R5).
NON_PRODUCT_CODE_PREFIXES: tuple[str, ...] = ("GIFT_",)


def non_product_mask(stock_codes: pd.Series) -> pd.Series:
    """Return a boolean Series: True where the stock code is not a product (rule R5).

    Codes are stripped and upper-cased first, so ``post`` and ``gift_0001_20`` match.
    Missing values are never non-product.
    """
    codes = stock_codes.astype(str).str.strip().str.upper().fillna("")
    by_code = codes.isin(list(NON_PRODUCT_STOCK_CODES))
    by_prefix = codes.str.startswith(NON_PRODUCT_CODE_PREFIXES)
    return by_code | by_prefix
