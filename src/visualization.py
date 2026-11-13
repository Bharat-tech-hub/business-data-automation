"""Chart functions. static_* return Matplotlib Figures (for PDF reports);
interactive_* return Plotly Figures (for the dashboard). Nothing is shown or saved here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure
from plotly.subplots import make_subplots

from src.analytics import monthly_trend, rfm_table
from src.kpis import KpiFilter, apply_filter, customer_frequency, revenue_by_country, revenue_by_product

NO_DATA = "No data for the selected filters"
MAIN_COLOR = "#1f77b4"
PARTIAL_COLOR = "#aec7e8"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _empty_static(title: str) -> Figure:
    fig = Figure(figsize=(8, 3))
    ax = fig.subplots()
    ax.text(0.5, 0.5, NO_DATA, ha="center", va="center", transform=ax.transAxes)
    ax.set_title(title)
    ax.axis("off")
    return fig


def _empty_interactive(title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=NO_DATA, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    fig.update_layout(title=title, xaxis_visible=False, yaxis_visible=False)
    return fig


def _product_labels(table: pd.DataFrame) -> list[str]:
    if "name" in table.columns:
        return [f"{code} - {str(name)[:30]}" for code, name in zip(table.index, table["name"])]
    return [str(code) for code in table.index]


def _weekday_hour(df, flt):
    d = apply_filter(df, flt)
    s = d.loc[d["is_sale"]]
    if s.empty:
        return None
    by_day = s.groupby(s["InvoiceDate"].dt.day_name())["LineTotal"].sum().reindex(WEEKDAYS, fill_value=0.0)
    by_hour = s.groupby(s["InvoiceDate"].dt.hour)["LineTotal"].sum().reindex(range(24), fill_value=0.0)
    return by_day, by_hour


def static_monthly_revenue(df, flt: KpiFilter | None = None) -> Figure:
    title = "Monthly gross sales"
    m = monthly_trend(df, flt)
    if m.empty:
        return _empty_static(title)
    fig = Figure(figsize=(10, 4))
    ax = fig.subplots()
    ax.bar(m.index, m["revenue"], color=[PARTIAL_COLOR if p else MAIN_COLOR for p in m["partial"]])
    ax.set_title(title + " (lighter bar = partial month)")
    ax.set_ylabel("Currency units")
    ax.tick_params(axis="x", rotation=60)
    fig.tight_layout()
    return fig


def static_top_products(df, names=None, flt: KpiFilter | None = None, n: int = 10) -> Figure:
    title = f"Top {n} products by revenue"
    table = revenue_by_product(df, names, flt).head(n)
    if table.empty:
        return _empty_static(title)
    table = table.iloc[::-1]
    fig = Figure(figsize=(9, 5))
    ax = fig.subplots()
    ax.barh(range(len(table)), table["revenue"], color=MAIN_COLOR)
    ax.set_yticks(range(len(table)))
    ax.set_yticklabels(_product_labels(table))
    ax.set_title(title)
    ax.set_xlabel("Currency units")
    fig.tight_layout()
    return fig


def static_country_revenue(df, flt: KpiFilter | None = None, exclude_top: bool = False, n: int = 10) -> Figure:
    title = "Revenue by country" + (" (largest market excluded)" if exclude_top else "")
    t = revenue_by_country(df, flt)
    if exclude_top:
        t = t.iloc[1:]
    t = t.head(n)
    if t.empty:
        return _empty_static(title)
    t = t.iloc[::-1]
    fig = Figure(figsize=(9, 5))
    ax = fig.subplots()
    ax.barh(range(len(t)), t["revenue"], color=MAIN_COLOR)
    ax.set_yticks(range(len(t)))
    ax.set_yticklabels([str(c) for c in t.index])
    ax.set_title(title)
    ax.set_xlabel("Currency units")
    fig.tight_layout()
    return fig


def static_weekday_hour(df, flt: KpiFilter | None = None) -> Figure:
    title = "Revenue by weekday and hour"
    parts = _weekday_hour(df, flt)
    if parts is None:
        return _empty_static(title)
    by_day, by_hour = parts
    fig = Figure(figsize=(12, 4))
    ax1, ax2 = fig.subplots(1, 2)
    ax1.bar(WEEKDAYS, by_day.values, color=MAIN_COLOR)
    ax1.set_title("Revenue by weekday")
    ax1.tick_params(axis="x", rotation=45)
    ax1.set_ylabel("Currency units")
    ax2.bar(by_hour.index, by_hour.values, color=MAIN_COLOR)
    ax2.set_title("Revenue by hour of day")
    ax2.set_xlabel("Hour")
    fig.tight_layout()
    return fig


def static_customer_spend(df, flt: KpiFilter | None = None) -> Figure:
    title = "Customer spend distribution (log scale)"
    spend = customer_frequency(df, flt)["spend"]
    spend = spend[spend > 0]
    if spend.empty:
        return _empty_static(title)
    lo, hi = float(spend.min()), float(spend.max())
    bins = np.logspace(np.log10(lo), np.log10(hi), 40) if lo < hi else [lo * 0.9, hi * 1.1]
    fig = Figure(figsize=(8, 4))
    ax = fig.subplots()
    ax.hist(spend, bins=bins, color=MAIN_COLOR)
    ax.set_xscale("log")
    ax.set_title(title)
    ax.set_xlabel("Spend per customer (currency units)")
    ax.set_ylabel("Customers")
    fig.tight_layout()
    return fig


def static_rfm(df, flt: KpiFilter | None = None) -> Figure:
    title = "Customers: recency vs frequency"
    r = rfm_table(df, flt)
    if r.empty:
        return _empty_static(title)
    fig = Figure(figsize=(8, 5))
    ax = fig.subplots()
    ax.scatter(r["recency_days"], r["frequency"], s=12, alpha=0.5, color=MAIN_COLOR)
    ax.set_yscale("log")
    ax.set_title(title)
    ax.set_xlabel("Days since last order")
    ax.set_ylabel("Orders (log scale)")
    fig.tight_layout()
    return fig


def interactive_monthly_revenue(df, flt: KpiFilter | None = None) -> go.Figure:
    title = "Monthly gross sales"
    m = monthly_trend(df, flt)
    if m.empty:
        return _empty_interactive(title)
    fig = go.Figure(go.Bar(
        x=list(m.index), y=m["revenue"].tolist(),
        marker_color=[PARTIAL_COLOR if p else MAIN_COLOR for p in m["partial"]],
        customdata=m["partial"].tolist(),
        hovertemplate="%{x}<br>%{y:,.2f}<br>partial month: %{customdata}<extra></extra>",
    ))
    fig.update_layout(title=title + " (lighter bar = partial month)", yaxis_title="Currency units")
    return fig


def interactive_top_products(df, names=None, flt: KpiFilter | None = None, n: int = 10) -> go.Figure:
    title = f"Top {n} products by revenue"
    table = revenue_by_product(df, names, flt).head(n)
    if table.empty:
        return _empty_interactive(title)
    table = table.iloc[::-1]
    fig = go.Figure(go.Bar(x=table["revenue"].tolist(), y=_product_labels(table), orientation="h", marker_color=MAIN_COLOR))
    fig.update_layout(title=title, xaxis_title="Currency units")
    return fig


def interactive_country_revenue(df, flt: KpiFilter | None = None, exclude_top: bool = False, n: int = 10) -> go.Figure:
    title = "Revenue by country" + (" (largest market excluded)" if exclude_top else "")
    t = revenue_by_country(df, flt)
    if exclude_top:
        t = t.iloc[1:]
    t = t.head(n)
    if t.empty:
        return _empty_interactive(title)
    t = t.iloc[::-1]
    fig = go.Figure(go.Bar(x=t["revenue"].tolist(), y=[str(c) for c in t.index], orientation="h", marker_color=MAIN_COLOR))
    fig.update_layout(title=title, xaxis_title="Currency units")
    return fig


def interactive_weekday_hour(df, flt: KpiFilter | None = None) -> go.Figure:
    title = "Revenue by weekday and hour"
    parts = _weekday_hour(df, flt)
    if parts is None:
        return _empty_interactive(title)
    by_day, by_hour = parts
    fig = make_subplots(rows=1, cols=2, subplot_titles=("By weekday", "By hour of day"))
    fig.add_trace(go.Bar(x=WEEKDAYS, y=by_day.tolist(), marker_color=MAIN_COLOR), row=1, col=1)
    fig.add_trace(go.Bar(x=list(by_hour.index), y=by_hour.tolist(), marker_color=MAIN_COLOR), row=1, col=2)
    fig.update_layout(title=title, showlegend=False)
    return fig


def interactive_rfm(df, flt: KpiFilter | None = None) -> go.Figure:
    title = "Customers: recency vs frequency"
    r = rfm_table(df, flt)
    if r.empty:
        return _empty_interactive(title)
    fig = go.Figure(go.Scatter(
        x=r["recency_days"].tolist(), y=r["frequency"].tolist(), mode="markers",
        text=[f"Customer {c}" for c in r.index], marker={"color": MAIN_COLOR, "opacity": 0.5, "size": 6},
    ))
    fig.update_layout(title=title, xaxis_title="Days since last order", yaxis_title="Orders (log scale)", yaxis_type="log")
    return fig
