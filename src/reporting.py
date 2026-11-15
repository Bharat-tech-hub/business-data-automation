"""Excel (and later PDF) report generation. Returns bytes so the dashboard can offer downloads."""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import xlsxwriter

from config.settings import settings
from src.analytics import monthly_trend, observations, rfm_table, spend_concentration
from src.cleaning import CleaningReport
from src.ingestion import sanitize_filename
from src.kpis import KpiFilter, compute_kpis, customer_frequency, revenue_by_country, revenue_by_product
from src.validation import ValidationReport

NOTES = (
    "Amounts are in currency units (the dataset states no currency).",
    "Partial months are incomplete; they are shown but excluded from growth rates.",
    "Returns are cancelled invoices, not linked to original sales (rule R10); the return rate is a ratio of totals.",
    "Customer figures cover only rows with a CustomerID (rule R6).",
)


@dataclass
class ReportContext:
    """Everything a report needs besides the cleaned DataFrame."""

    flt: KpiFilter | None = None
    names: pd.Series | None = None
    validation: ValidationReport | None = None
    cleaning: CleaningReport | None = None
    report_date: date | None = None


def describe_filter(flt: KpiFilter | None) -> list[str]:
    """Human-readable filter lines."""
    if flt is None:
        return ["No filters applied (all data)."]
    lines = []
    if flt.start_date is not None:
        lines.append(f"From: {pd.Timestamp(flt.start_date).date()}")
    if flt.end_date is not None:
        lines.append(f"To: {pd.Timestamp(flt.end_date).date()}")
    if flt.countries:
        lines.append("Countries: " + ", ".join(flt.countries))
    return lines or ["No filters applied (all data)."]


def kpi_rows(df: pd.DataFrame, flt: KpiFilter | None) -> list[tuple[str, float, str]]:
    """KPI label, value, and format key ('money', 'int' or 'pct')."""
    k = compute_kpis(df, flt)
    return [
        ("Gross sales", k.gross_sales, "money"),
        ("Returns value", k.returns_value, "money"),
        ("Net revenue", k.net_revenue, "money"),
        ("Orders", k.orders, "int"),
        ("Units sold", k.units_sold, "int"),
        ("Average order value", k.average_order_value, "money"),
        ("Average selling price", k.average_selling_price, "money"),
        ("Return rate", k.return_rate, "pct"),
        ("Shipping and fees", k.shipping_and_fees, "money"),
    ]


def _formats(wb) -> dict:
    return {
        "title": wb.add_format({"bold": True, "font_size": 16}),
        "bold": wb.add_format({"bold": True}),
        "header": wb.add_format({"bold": True, "bg_color": "#DCE6F1", "border": 1}),
        "money": wb.add_format({"num_format": "#,##0.00"}),
        "int": wb.add_format({"num_format": "#,##0"}),
        "pct": wb.add_format({"num_format": "0.0%"}),
    }


def _write_table(ws, df: pd.DataFrame, fmts: dict, money=(), pct=(), start_row: int = 0) -> None:
    """Write a DataFrame with a header row, widths, formats and a frozen header."""
    cols = list(df.columns)
    for c, name in enumerate(cols):
        ws.write(start_row, c, str(name), fmts["header"])
    for r, row in enumerate(df.itertuples(index=False), start=start_row + 1):
        for c, value in enumerate(row):
            name = cols[c]
            if value is None or (not isinstance(value, str) and pd.isna(value)):
                ws.write_blank(r, c, None)
            elif isinstance(value, (bool,)) or str(type(value).__name__) == "bool_":
                ws.write_boolean(r, c, bool(value))
            elif name in money:
                ws.write_number(r, c, float(value), fmts["money"])
            elif name in pct:
                ws.write_number(r, c, float(value), fmts["pct"])
            elif isinstance(value, (int, float)) or hasattr(value, "dtype"):
                ws.write_number(r, c, float(value))
            else:
                ws.write(r, c, str(value))
    for c, name in enumerate(cols):
        longest = max([len(str(name))] + [len(str(v)) for v in df.iloc[:, c].head(200)])
        ws.set_column(c, c, min(max(longest + 2, 10), 60))
    ws.freeze_panes(start_row + 1, 0)


def _summary_sheet(wb, df, ctx, fmts) -> None:
    ws = wb.add_worksheet("Summary")
    ws.set_column(0, 0, 40)
    ws.set_column(1, 1, 22)
    ws.set_column(2, 8, 12)
    wrap = wb.add_format({"text_wrap": True, "valign": "top"})
    ws.write(0, 0, "Business Sales Report", fmts["title"])
    ws.write(1, 0, "Report date")
    ws.write(1, 1, str(ctx.report_date or date.today()))
    ws.write(2, 0, "Filters", fmts["bold"])
    row = 3
    for line in describe_filter(ctx.flt):
        ws.write(row, 0, line)
        row += 1
    row += 1
    ws.write(row, 0, "KPI", fmts["header"])
    ws.write(row, 1, "Value", fmts["header"])
    row += 1
    for label, value, kind in kpi_rows(df, ctx.flt):
        ws.write(row, 0, label)
        ws.write_number(row, 1, float(value), fmts[kind])
        row += 1
    row += 1
    ws.write(row, 0, "Observations (computed from the data)", fmts["bold"])
    row += 1
    for line in observations(df, ctx.names, ctx.flt):
        ws.merge_range(row, 0, row, 8, line, wrap)
        ws.set_row(row, 30)
        row += 1
    row += 1
    ws.write(row, 0, "Notes", fmts["bold"])
    row += 1
    for line in NOTES:
        ws.merge_range(row, 0, row, 8, line, wrap)
        ws.set_row(row, 30)
        row += 1


def _monthly_sheet(wb, df, ctx, fmts) -> None:
    ws = wb.add_worksheet("Monthly")
    m = monthly_trend(df, ctx.flt)
    m = m.rename_axis("month").reset_index()
    _write_table(ws, m, fmts, money=("revenue",), pct=("growth",))
    if len(m):
        chart = wb.add_chart({"type": "column"})
        chart.add_series({
            "name": "Gross sales",
            "categories": ["Monthly", 1, 0, len(m), 0],
            "values": ["Monthly", 1, 1, len(m), 1],
        })
        chart.set_title({"name": "Monthly gross sales (currency units)"})
        chart.set_legend({"none": True})
        ws.insert_chart(1, 6, chart)


def _tables_sheets(wb, df, ctx, fmts) -> None:
    p = revenue_by_product(df, ctx.names, ctx.flt).head(100).reset_index()
    _write_table(wb.add_worksheet("Products"), p, fmts, money=("revenue",), pct=("share", "cumulative_share"))
    c = revenue_by_country(df, ctx.flt).reset_index()
    _write_table(wb.add_worksheet("Countries"), c, fmts, money=("revenue",), pct=("share",))


def _customers_sheet(wb, df, ctx, fmts) -> None:
    ws = wb.add_worksheet("Customers")
    freq = customer_frequency(df, ctx.flt)
    rfm = rfm_table(df, ctx.flt)
    stats = [
        ("Identified customers", len(freq), "int"),
        ("Repeat customers (more than one order)", int((freq["orders"] > 1).sum()) if len(freq) else 0, "int"),
        ("Top 10% of customers: share of spend", spend_concentration(df, ctx.flt), "pct"),
        ("Median recency (days)", float(rfm["recency_days"].median()) if len(rfm) else 0.0, "money"),
    ]
    ws.set_column(0, 0, 42)
    ws.set_column(1, 2, 16)
    for r, (label, value, kind) in enumerate(stats):
        ws.write(r, 0, label)
        ws.write_number(r, 1, float(value), fmts[kind])
    top = freq.sort_values("spend", ascending=False).head(50).reset_index()
    ws.write(len(stats) + 1, 0, "Top 50 customers by spend", fmts["bold"])
    for ci, name in enumerate(top.columns):
        ws.write(len(stats) + 2, ci, str(name), fmts["header"])
    for ri, rv in enumerate(top.itertuples(index=False), start=len(stats) + 3):
        ws.write(ri, 0, str(rv[0]))
        ws.write_number(ri, 1, float(rv[1]))
        ws.write_number(ri, 2, float(rv[2]), fmts["money"])


def _quality_sheet(wb, ctx, fmts) -> None:
    ws = wb.add_worksheet("Data quality")
    ws.set_column(0, 0, 36)
    ws.set_column(1, 1, 38)
    ws.set_column(2, 3, 14)
    ws.set_column(4, 4, 80)
    r0 = 0
    if ctx.validation is not None:
        ws.write(r0, 0, "Validation findings", fmts["bold"])
        vt = ctx.validation.to_frame()
        for ci, name in enumerate(vt.columns):
            ws.write(r0 + 1, ci, str(name), fmts["header"])
        for ri, rv in enumerate(vt.itertuples(index=False), start=r0 + 2):
            for ci, value in enumerate(rv):
                if value is None or (not isinstance(value, str) and pd.isna(value)):
                    ws.write_blank(ri, ci, None)
                elif isinstance(value, str):
                    ws.write(ri, ci, value)
                else:
                    ws.write_number(ri, ci, float(value))
        r0 += len(vt) + 3
    if ctx.cleaning is not None:
        ws.write(r0, 0, "Cleaning audit trail", fmts["bold"])
        ct = ctx.cleaning.to_frame()
        for ci, name in enumerate(ct.columns):
            ws.write(r0 + 1, ci, str(name), fmts["header"])
        for ri, rv in enumerate(ct.itertuples(index=False), start=r0 + 2):
            ws.write(ri, 0, str(rv[0]))
            ws.write_number(ri, 1, float(rv[1]), fmts["int"])
            ws.write(ri, 2, str(rv[2]))
    if ctx.validation is None and ctx.cleaning is None:
        ws.write(0, 0, "No validation or cleaning information was supplied.")


def build_excel(df: pd.DataFrame, ctx: ReportContext | None = None) -> bytes:
    """Build the Excel report and return the .xlsx file as bytes."""
    ctx = ctx or ReportContext()
    buffer = io.BytesIO()
    wb = xlsxwriter.Workbook(buffer, {"in_memory": True})
    fmts = _formats(wb)
    _summary_sheet(wb, df, ctx, fmts)
    _monthly_sheet(wb, df, ctx, fmts)
    _tables_sheets(wb, df, ctx, fmts)
    _customers_sheet(wb, df, ctx, fmts)
    _quality_sheet(wb, ctx, fmts)
    wb.close()
    return buffer.getvalue()


def save_report(data: bytes, file_name: str, directory: Path | None = None) -> Path:
    """Write report bytes into the reports folder with a sanitised name (.xlsx or .pdf only)."""
    safe = sanitize_filename(file_name)
    if Path(safe).suffix.lower() not in (".xlsx", ".pdf"):
        raise ValueError("Reports must be saved as .xlsx or .pdf")
    target_dir = directory or settings.reports_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe
    target.write_bytes(data)
    return target
