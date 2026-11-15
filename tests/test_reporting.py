"""Tests for src.reporting: read the generated workbook back and compare with hand values."""

import io
from datetime import date

import pytest
from openpyxl import load_workbook

from src.kpis import KpiFilter
from src.reporting import ReportContext, build_excel, describe_filter, save_report
from src.validation import validate
from tests.test_analytics import make_df


def _wb(ctx=None):
    return load_workbook(io.BytesIO(build_excel(make_df(), ctx)))


def _kv(ws):
    return {r[0].value: r[1].value for r in ws.iter_rows(min_row=1, max_row=40) if r[0].value and r[1].value is not None}


def test_sheets_present():
    assert _wb().sheetnames == ["Summary", "Monthly", "Products", "Countries", "Customers", "Data quality"]


def test_summary_kpis_match_hand_values():
    k = _kv(_wb(ReportContext(report_date=date(2011, 5, 1)))["Summary"])
    assert k["Gross sales"] == pytest.approx(440.0)
    assert k["Orders"] == 5
    assert k["Units sold"] == 6
    assert k["Average order value"] == pytest.approx(88.0)
    assert k["Net revenue"] == pytest.approx(440.0)
    assert k["Report date"] == "2011-05-01"


def test_filter_changes_numbers_and_is_described():
    wb = load_workbook(io.BytesIO(build_excel(make_df(), ReportContext(flt=KpiFilter(countries=("France",))))))
    k = _kv(wb["Summary"])
    assert k["Gross sales"] == pytest.approx(250.0)
    assert k["Orders"] == 2
    texts = [c.value for row in wb["Summary"].iter_rows() for c in row if c.value]
    assert "Countries: France" in texts


def test_monthly_sheet_values():
    ws = _wb()["Monthly"]
    rows = [[c.value for c in r][:4] for r in ws.iter_rows(min_row=2, max_row=5)]
    assert [r[0] for r in rows] == ["2011-01", "2011-02", "2011-03", "2011-04"]
    assert [r[1] for r in rows] == pytest.approx([100.0, 100.0, 200.0, 40.0])
    assert rows[3][2] in (True, 1)


def test_products_and_countries_sheets():
    wb = _wb()
    assert wb["Products"]["A2"].value == "P2"
    assert [r[0].value for r in wb["Countries"].iter_rows(min_row=2, max_row=3)] == ["France", "United Kingdom"]


def test_money_format_and_frozen_header():
    ws = _wb()["Monthly"]
    assert ws["B2"].number_format == "#,##0.00"
    assert ws.freeze_panes == "A2"


def test_data_quality_sheet_with_validation():
    from src.schema import REQUIRED_COLUMNS
    raw = make_df()[list(REQUIRED_COLUMNS)]
    wb = _wb(ReportContext(validation=validate(raw)))
    assert wb["Data quality"]["A1"].value == "Validation findings"


def test_empty_selection_still_builds():
    data = build_excel(make_df(), ReportContext(flt=KpiFilter(countries=("Nowhere",))))
    k = _kv(load_workbook(io.BytesIO(data))["Summary"])
    assert k["Gross sales"] == 0
    assert k["Orders"] == 0


def test_describe_filter():
    assert describe_filter(None) == ["No filters applied (all data)."]
    assert "From: 2011-01-01" in describe_filter(KpiFilter(start_date="2011-01-01"))


def test_save_report_sanitises_and_restricts(tmp_path):
    path = save_report(b"abc", "../../my report!.xlsx", tmp_path)
    assert path.parent == tmp_path and path.name == "my report_.xlsx"
    assert path.read_bytes() == b"abc"
    with pytest.raises(ValueError):
        save_report(b"abc", "evil.exe", tmp_path)
