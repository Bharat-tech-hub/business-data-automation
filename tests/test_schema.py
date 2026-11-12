"""Tests for src.schema."""

from src.schema import (
    CANCELLATION_PREFIX,
    NON_PRODUCT_STOCK_CODES,
    REQUIRED_COLUMNS,
    TEXT_ID_COLUMNS,
)


def test_required_columns_match_dataset_schema():
    assert REQUIRED_COLUMNS == (
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
    )


def test_required_columns_are_unique():
    assert len(set(REQUIRED_COLUMNS)) == len(REQUIRED_COLUMNS)


def test_text_id_columns_are_required_columns():
    assert set(TEXT_ID_COLUMNS) <= set(REQUIRED_COLUMNS)


def test_non_product_codes_are_uppercase():
    assert all(code == code.upper() for code in NON_PRODUCT_STOCK_CODES)


def test_known_codes_and_prefix():
    assert {"POST", "DOT", "M", "BANK CHARGES"} <= NON_PRODUCT_STOCK_CODES
    assert "m".upper() in NON_PRODUCT_STOCK_CODES
    assert CANCELLATION_PREFIX == "C"
