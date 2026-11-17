import io

import pandas as pd
import pytest
from openpyxl import load_workbook

from src.cleaning import clean
from src.kpis import KpiFilter
from src.reporting import ReportContext, build_excel, build_pdf, save_report
from src.schema import REQUIRED_COLUMNS

EMPTY = KpiFilter(start_date="2100-01-01")


def make_df() -> pd.DataFrame:
    rows = [
        ["1", "A1", "ITEM A", 1, "2011-01-01 09:00:00", 100.0, 1, "United Kingdom"],
        ["2", "A1", "ITEM A", 1, "2011-02-10 09:00:00", 50.0, 1, "United Kingdom"],
        ["3", "P2", "ITEM P", 1, "2011-02-11 09:00:00", 50.0, 2, "France"],
        ["4", "P2", "ITEM P", 2, "2011-03-12 09:00:00", 100.0, 2, "France"],
        ["5", "C1", "ITEM C", 1, "2011-04-15 09:00:00", 40.0, 3, "United Kingdom"],
    ]
    cleaned, _ = clean(pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS)))
    return cleaned


def test_build_excel_empty_selection():
    data = build_excel(make_df(), ReportContext(flt=EMPTY))
    wb = load_workbook(io.BytesIO(data))
    assert "Summary" in wb.sheetnames
    cells = [c for row in wb["Summary"].iter_rows(values_only=True) for c in row]
    assert "No sales in the selected data." in cells


def test_build_pdf_empty_selection():
    data = build_pdf(make_df(), ReportContext(flt=EMPTY))
    assert data.startswith(b"%PDF-") 
def test_save_report_writes_bytes(tmp_path):
    target = save_report(b"abc", "x.xlsx", tmp_path)
    assert target.name == "x.xlsx"
    assert target.read_bytes() == b"abc"


def test_save_report_sanitises_name(tmp_path):
    target = save_report(b"abc", "../evil.xlsx", tmp_path)
    assert target.parent == tmp_path
    assert target.name == "evil.xlsx"


def test_save_report_rejects_other_extensions(tmp_path):
    with pytest.raises(ValueError):
        save_report(b"abc", "run.exe", tmp_path)


def test_save_report_creates_missing_directory(tmp_path):
    target = save_report(b"abc", "x.pdf", tmp_path / "new" / "reports")
    assert target.exists()
