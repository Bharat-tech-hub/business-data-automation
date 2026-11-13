"""Tests for src.validation. Each test changes one thing in 20 valid rows."""

import pandas as pd
import pytest

from src.schema import REQUIRED_COLUMNS
from src.validation import BLOCKING_THRESHOLD, Severity, validate


def base_rows(n: int = 20) -> list[list]:
    return [
        [
            f"5000{i:02d}",
            f"2000{i:02d}",
            f"ITEM {i}",
            2,
            "2011-01-01 10:00:00",
            1.5,
            f"1{i:04d}",
            "United Kingdom",
        ]
        for i in range(n)
    ]


def frame(rows: list[list]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS))


def test_clean_data_has_no_findings():
    report = validate(frame(base_rows()))
    assert report.findings == []
    assert report.total_rows == 20
    assert report.sale_rows == 20
    assert report.has_blocking_errors is False


def test_missing_required_column_raises():
    with pytest.raises(ValueError, match="Country"):
        validate(frame(base_rows()).drop(columns="Country"))


def test_empty_dataframe_is_blocking():
    report = validate(frame([]))
    assert report.total_rows == 0
    assert report.has_blocking_errors is True
    assert report.get("empty_dataset") is not None


def test_missing_customer_id_counted():
    rows = base_rows()
    rows[0][6] = None
    rows[1][6] = None
    finding = validate(frame(rows)).get("missing_customerid")
    assert finding.count == 2
    assert finding.severity is Severity.WARNING
    assert finding.share == pytest.approx(0.1)


def test_blank_description_counts_as_missing():
    rows = base_rows()
    rows[0][2] = "   "
    assert validate(frame(rows)).get("missing_description").count == 1


def test_exact_duplicate_row_counted():
    rows = base_rows()
    rows.append(list(rows[0]))
    report = validate(frame(rows))
    assert report.total_rows == 21
    assert report.get("duplicate_rows").count == 1


def test_cancelled_row_is_info_and_not_a_sale():
    rows = base_rows()
    rows[0][0] = "C500000"
    rows[0][3] = -2
    report = validate(frame(rows))
    assert report.get("cancelled_rows").count == 1
    assert report.get("cancelled_rows").severity is Severity.INFO
    assert report.get("nonpositive_quantity_non_cancelled") is None
    assert report.sale_rows == 19


def test_nonpositive_quantity_on_non_cancelled_invoice():
    rows = base_rows()
    rows[0][3] = 0
    rows[1][3] = -5
    report = validate(frame(rows))
    assert report.get("nonpositive_quantity_non_cancelled").count == 2
    assert report.sale_rows == 18


def test_zero_price_with_positive_quantity():
    rows = base_rows()
    rows[0][5] = 0.0
    report = validate(frame(rows))
    assert report.get("zero_price_positive_quantity").count == 1
    assert report.sale_rows == 19


def test_negative_price():
    rows = base_rows()
    rows[0][5] = -10.0
    report = validate(frame(rows))
    assert report.get("negative_price").count == 1
    assert report.get("zero_price_positive_quantity") is None
    assert report.sale_rows == 19


def test_non_product_codes_case_insensitive():
    rows = base_rows()
    rows[0][1] = "post"
    rows[1][1] = "BANK CHARGES"
    report = validate(frame(rows))
    assert report.get("non_product_codes").count == 2
    assert report.sale_rows == 18


def test_one_bad_date_is_warning_at_exactly_threshold():
    rows = base_rows()
    rows[5][4] = "not a date"
    finding = validate(frame(rows)).get("unusable_invoicedate")
    assert finding.count == 1
    assert finding.severity is Severity.WARNING  # 1 of 20 = 5%, not above 5%


def test_two_bad_dates_are_blocking():
    rows = base_rows()
    rows[5][4] = "not a date"
    rows[6][4] = "also bad"
    report = validate(frame(rows))
    assert report.get("unusable_invoicedate").severity is Severity.BLOCKING
    assert report.has_blocking_errors is True


def test_missing_date_counts_as_unusable_not_as_missing():
    rows = base_rows()
    rows[3][4] = None
    report = validate(frame(rows))
    assert report.get("unusable_invoicedate").count == 1
    assert report.get("missing_invoicedate") is None


def test_non_numeric_quantity_blocking():
    rows = base_rows()
    rows[2][3] = "abc"
    rows[3][3] = "abc"
    report = validate(frame(rows))
    assert report.get("unusable_quantity").count == 2
    assert report.get("unusable_quantity").severity is Severity.BLOCKING
    assert report.sale_rows == 18


def test_single_non_numeric_price_is_warning():
    rows = base_rows()
    rows[0][5] = "free"
    report = validate(frame(rows))
    assert report.get("unusable_unitprice").count == 1
    assert report.get("unusable_unitprice").severity is Severity.WARNING
    assert report.sale_rows == 19


def test_no_sale_rows_is_blocking():
    rows = base_rows()
    for row in rows:
        row[0] = "C" + row[0]
        row[3] = -2
    report = validate(frame(rows))
    assert report.sale_rows == 0
    assert report.get("cancelled_rows").count == 20
    assert report.get("no_sale_rows").severity is Severity.BLOCKING


def test_mixed_type_invoice_numbers_reported():
    rows = base_rows()
    rows[0][0] = 536365  # a number among text values, as in real XLSX files
    report = validate(frame(rows))
    assert report.get("mixed_type_invoiceno").count == 1
    assert report.get("mixed_type_invoiceno").severity is Severity.INFO
    assert report.sale_rows == 20


def test_duplicate_headers_flagged():
    df = frame(base_rows())
    df["Country.1"] = "x"
    finding = validate(df).get("duplicate_headers")
    assert finding.count == 1
    assert finding.share is None


def test_findings_are_ordered_blocking_first():
    rows = base_rows()
    rows[5][4] = "bad"
    rows[6][4] = "bad"
    rows[0][0] = "C500000"
    rows[0][3] = -2
    rows.append(list(rows[1]))
    report = validate(frame(rows))
    ranks = [{"blocking": 0, "warning": 1, "info": 2}[f.severity.value] for f in report.findings]
    assert ranks == sorted(ranks)
    assert report.findings[0].severity is Severity.BLOCKING


def test_to_frame_columns_and_values():
    rows = base_rows()
    rows[0][6] = None
    table = validate(frame(rows)).to_frame()
    assert list(table.columns) == ["severity", "code", "count", "share_pct", "message"]
    assert len(table) == 1
    assert table.loc[0, "code"] == "missing_customerid"
    assert table.loc[0, "count"] == 1
    assert table.loc[0, "share_pct"] == pytest.approx(5.0)


def test_validate_does_not_modify_input():
    rows = base_rows()
    rows[0][6] = None
    rows[1][4] = "bad"
    df = frame(rows)
    before = df.copy()
    validate(df)
    pd.testing.assert_frame_equal(df, before)


def test_threshold_constant():
    assert BLOCKING_THRESHOLD == 0.05


def test_native_numeric_and_datetime_dtypes_accepted():
    df = frame(base_rows())
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    assert df["Quantity"].dtype.kind == "i"
    assert validate(df).findings == []
