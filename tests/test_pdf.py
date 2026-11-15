"""Tests for build_pdf: structure only (no PDF text reader is installed)."""

import re

import pandas as pd

from src.kpis import KpiFilter
from src.reporting import ReportContext, build_pdf, save_report
from src.schema import REQUIRED_COLUMNS
from src.validation import validate
from tests.test_analytics import make_df


def _pages(data: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", data))


def test_pdf_header_and_trailer():
    data = build_pdf(make_df())
    assert data.startswith(b"%PDF-")
    assert b"%%EOF" in data[-1024:]


def test_pdf_has_multiple_pages():
    assert _pages(build_pdf(make_df())) >= 2


def test_pdf_builds_for_empty_selection():
    data = build_pdf(make_df(), ReportContext(flt=KpiFilter(countries=("Nowhere",))))
    assert data.startswith(b"%PDF-")


def test_pdf_with_data_quality_differs():
    raw = make_df()[list(REQUIRED_COLUMNS)]
    plain = build_pdf(make_df())
    with_dq = build_pdf(make_df(), ReportContext(validation=validate(raw)))
    assert len(with_dq) != len(plain)


def test_pdf_escapes_markup_in_names():
    names = pd.Series({"P2": "Salt & <Pepper>"})
    assert build_pdf(make_df(), ReportContext(names=names)).startswith(b"%PDF-")


def test_save_pdf(tmp_path):
    path = save_report(build_pdf(make_df()), "report.pdf", tmp_path)
    assert path.read_bytes().startswith(b"%PDF-")
