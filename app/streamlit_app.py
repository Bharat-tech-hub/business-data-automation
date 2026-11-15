"""Business Data Analysis dashboard (Streamlit). Launch with: python run.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from config.settings import settings
from src.analytics import monthly_trend, observations
from src.cleaning import build_product_names, clean
from src.ingestion import IngestionError, load_bytes
from src.kpis import KpiFilter, compute_kpis
from src.logger import setup_logging
from src import visualization as viz
from src.validation import validate

st.set_page_config(page_title="Business Data Analysis", layout="wide")
setup_logging()

PAGES = [
    "Executive overview", "Sales analytics", "Product analytics", "Customer analytics",
    "Geographic analytics", "Data quality", "Report downloads",
]


@st.cache_data(show_spinner="Loading, validating and cleaning data...")
def run_pipeline(data: bytes, file_name: str):
    """Ingest, validate and clean. Cached on the file bytes and name."""
    raw, ingestion = load_bytes(data, file_name)
    validation = validate(raw)
    if validation.has_blocking_errors:
        return None, ingestion, validation, None, None
    cleaned, cleaning = clean(raw)
    names = build_product_names(cleaned)
    return cleaned, ingestion, validation, cleaning, names


def get_source() -> tuple[bytes, str] | None:
    """Return (bytes, name) from an upload or from data/raw, or None."""
    st.sidebar.header("Data")
    upload = st.sidebar.file_uploader("Upload a CSV or XLSX file", type=["csv", "xlsx"])
    if upload is not None:
        return upload.getvalue(), upload.name
    files = sorted(p for p in settings.raw_data_dir.glob("*") if p.suffix.lower() in settings.allowed_extensions)
    if files and st.sidebar.checkbox(f"Use {files[0].name} from data/raw", value=True):
        return files[0].read_bytes(), files[0].name
    return None


def build_filter(df: pd.DataFrame) -> KpiFilter:
    """Sidebar filters -> KpiFilter."""
    st.sidebar.header("Filters")
    lo, hi = df["InvoiceDate"].min().date(), df["InvoiceDate"].max().date()
    picked = st.sidebar.date_input("Date range", value=(lo, hi), min_value=lo, max_value=hi)
    start, end = (picked if isinstance(picked, tuple) and len(picked) == 2 else (lo, hi))
    countries = st.sidebar.multiselect("Countries (empty = all)", sorted(df["Country"].unique()))
    return KpiFilter(start_date=pd.Timestamp(start), end_date=pd.Timestamp(end), countries=tuple(countries))


def page_overview(df: pd.DataFrame, names, flt: KpiFilter) -> None:
    st.title("Executive overview")
    k = compute_kpis(df, flt)
    for a, b in [
        (("Gross sales", f"{k.gross_sales:,.2f}"), ("Net revenue", f"{k.net_revenue:,.2f}")),
        (("Orders", f"{k.orders:,}"), ("Average order value", f"{k.average_order_value:,.2f}")),
        (("Units sold", f"{k.units_sold:,}"), ("Average selling price", f"{k.average_selling_price:,.2f}")),
        (("Return rate", f"{k.return_rate:.1%}"), ("Shipping and fees", f"{k.shipping_and_fees:,.2f}")),
    ]:
        c = st.columns(2)
        c[0].metric(*a)
        c[1].metric(*b)
    st.caption("Amounts are in currency units (the dataset states no currency).")
    st.plotly_chart(viz.interactive_monthly_revenue(df, flt), width="stretch")
    st.subheader("Observations (computed from the data)")
    for line in observations(df, names, flt):
        st.write("- " + line)


def main() -> None:
    source = get_source()
    page = st.sidebar.radio("Page", PAGES)
    if source is None:
        st.title("Business Data Analysis")
        st.info("Upload a CSV or XLSX file in the sidebar, or place one in data/raw/.")
        return
    try:
        df, ingestion, validation, cleaning, names = run_pipeline(*source)
    except IngestionError as exc:
        st.error(f"Could not load the file: {exc}")
        return
    for w in ingestion.warnings:
        st.sidebar.warning(w)
    if df is None:
        st.error("The data has blocking problems and cannot be analysed.")
        st.dataframe(validation.to_frame(), width="stretch")
        return
    flt = build_filter(df)
    if page == "Executive overview":
        page_overview(df, names, flt)
    else:
        st.title(page)
        st.info("This page is coming in the next step.")


main()
