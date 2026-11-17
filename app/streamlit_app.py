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
from src.analytics import country_performance, monthly_trend, observations, product_performance, quarterly_trend, spend_concentration
from src.cleaning import build_product_names, clean
from src.ingestion import IngestionError, load_bytes
from src.kpis import KpiFilter, apply_filter, compute_kpis, customer_frequency, repeat_customer_share
from src.logger import setup_logging
from src.reporting import ReportContext, build_excel, build_pdf
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


def page_sales(df: pd.DataFrame, names, flt: KpiFilter) -> None:
    st.title("Sales analytics")
    monthly = monthly_trend(df, flt)
    if monthly.empty:
        st.info("No sales for the selected filters.")
        return
    st.plotly_chart(viz.interactive_monthly_revenue(df, flt), width="stretch")
    st.subheader("Monthly gross sales")
    st.dataframe(monthly.rename(columns={"revenue": "gross_sales"}).style.format(
        {"gross_sales": "{:,.2f}", "growth": "{:+.1%}"}, na_rep="-"), width="stretch")
    st.caption("Partial months are shown but excluded from growth rates.")
    st.subheader("Quarterly gross sales")
    st.dataframe(quarterly_trend(df, flt).style.format(
        {"revenue": "{:,.2f}", "growth": "{:+.1%}"}, na_rep="-"), width="stretch")
    st.subheader("Weekday and hour patterns")
    st.plotly_chart(viz.interactive_weekday_hour(df, flt), width="stretch")


def page_products(df: pd.DataFrame, names, flt: KpiFilter) -> None:
    st.title("Product analytics")
    n = st.slider("Number of products", 5, 50, 10)
    perf = product_performance(df, names, flt, n=n)
    if perf["products"] == 0:
        st.info("No product sales for the selected filters.")
        return
    st.metric("Products sold", f"{perf['products']:,}")
    st.write(f"{perf['products_for_80pct']:,} products make up 80% of product revenue.")
    st.plotly_chart(viz.interactive_top_products(df, names, flt, n=n), width="stretch")
    fmt = {"revenue": "{:,.2f}", "units": "{:,.0f}", "share": "{:.1%}", "cumulative_share": "{:.1%}"}
    st.subheader(f"Top {n} products")
    st.dataframe(perf["top"].style.format(fmt), width="stretch")
    st.subheader(f"Bottom {n} products")
    st.dataframe(perf["bottom"].style.format(fmt), width="stretch")
    st.caption("Shipping, fees and vouchers are excluded from product tables (rule R5).")


def page_customers(df: pd.DataFrame, names, flt: KpiFilter) -> None:
    st.title("Customer analytics")
    freq = customer_frequency(df, flt)
    if freq.empty:
        st.info("No identified customers for the selected filters.")
        return
    c = st.columns(3)
    c[0].metric("Identified customers", f"{len(freq):,}")
    c[1].metric("Repeat customers", f"{repeat_customer_share(df, flt):.1%}")
    c[2].metric("Top 10% share of spend", f"{spend_concentration(df, flt):.1%}")
    d = apply_filter(df, flt)
    sales = d[d["is_sale"]]
    missing = int((~sales["has_customer"]).sum())
    st.caption(f"{missing:,} sale rows ({missing / max(len(sales), 1):.1%}) have no CustomerID and are excluded here (rule R6).")
    st.subheader("Spend per customer")
    st.pyplot(viz.static_customer_spend(df, flt))
    st.subheader("Recency vs frequency")
    st.plotly_chart(viz.interactive_rfm(df, flt), width="stretch")
    st.subheader("Top 20 customers by spend")
    top = freq.sort_values("spend", ascending=False).head(20)
    st.dataframe(top.style.format({"spend": "{:,.2f}"}), width="stretch")


def page_geography(df: pd.DataFrame, names, flt: KpiFilter) -> None:
    st.title("Geographic analytics")
    table = country_performance(df, flt)
    if table.empty:
        st.info("No sales for the selected filters.")
        return
    if len(table) == 1:
        st.caption(f"Only one country is selected: {table.index[0]}.")
    exclude = st.checkbox("Exclude the largest market from the chart", value=len(table) > 1, disabled=len(table) < 2)
    st.plotly_chart(viz.interactive_country_revenue(df, flt, exclude_top=exclude and len(table) > 1), width="stretch")
    st.subheader("Revenue by country")
    st.dataframe(table.style.format({"revenue": "{:,.2f}", "units": "{:,.0f}", "share": "{:.1%}",
                                     "revenue_per_order": "{:,.2f}"}), width="stretch")
    st.caption("Country labels are shown as supplied (e.g. EIRE, RSA, Unspecified).")


def page_quality(extra: dict) -> None:
    st.title("Data quality")
    ing = extra["ingestion"]
    st.write(f"**File:** {ing.file_name} | **Format:** {ing.file_format} | **Size:** {ing.size_bytes / 1024 / 1024:.1f} MB | "
             f"**Rows:** {ing.rows:,} | **Columns:** {ing.columns}")
    st.subheader("Validation findings")
    st.dataframe(extra["validation"].to_frame(), width="stretch")
    st.subheader("Cleaning audit trail")
    st.dataframe(extra["cleaning"].to_frame(), width="stretch")
    st.caption("Validation runs on the raw data; the audit trail shows every change made by cleaning.")


@st.cache_data(show_spinner="Building report...")
def _report_bytes(kind: str, start, end, countries: tuple, data: bytes, file_name: str) -> bytes:
    df, _, validation, cleaning, names = run_pipeline(data, file_name)
    flt = KpiFilter(start_date=start, end_date=end, countries=countries)
    ctx = ReportContext(flt=flt, names=names, validation=validation, cleaning=cleaning)
    return build_excel(df, ctx) if kind == "xlsx" else build_pdf(df, ctx)


def page_downloads(source: tuple[bytes, str], flt: KpiFilter) -> None:
    st.title("Report downloads")
    st.write("Reports use the current sidebar filters.")
    stamp = pd.Timestamp.today().strftime("%Y-%m-%d")
    args = (flt.start_date, flt.end_date, tuple(flt.countries), *source)
    c = st.columns(2)
    c[0].download_button("Download Excel report", _report_bytes("xlsx", *args), f"sales_report_{stamp}.xlsx",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    c[1].download_button("Download PDF report", _report_bytes("pdf", *args), f"sales_report_{stamp}.pdf",
                         "application/pdf")


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
    elif page == "Sales analytics":
        page_sales(df, names, flt)
    elif page == "Product analytics":
        page_products(df, names, flt)
    elif page == "Customer analytics":
        page_customers(df, names, flt)
    elif page == "Geographic analytics":
        page_geography(df, names, flt)
    elif page == "Data quality":
        page_quality({"ingestion": ingestion, "validation": validation, "cleaning": cleaning})
    elif page == "Report downloads":
        page_downloads(source, flt)
    else:
        st.title(page)
        st.info("This page is coming in the next step.")


main()
