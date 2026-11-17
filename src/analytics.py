"""Advanced analytics on the cleaned DataFrame (BUSINESS_RULES R1-R10).

All functions accept an optional KpiFilter. Partial periods are flagged and
excluded from growth rates. Observations are built from computed values only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.kpis import KpiFilter, apply_filter, compute_kpis, customer_frequency, revenue_by_country, revenue_by_product


def _sales(df: pd.DataFrame, flt: KpiFilter | None) -> pd.DataFrame:
    d = apply_filter(df, flt)
    return d.loc[d["is_sale"]]


def product_performance(df, names=None, flt=None, n: int = 10) -> dict:
    """Top and bottom n products by revenue, and how many make up 80% of revenue."""
    table = revenue_by_product(df, names, flt)
    if table.empty:
        return {"top": table, "bottom": table, "products": 0, "products_for_80pct": 0}
    n80 = int((table["cumulative_share"] < 0.8).sum()) + 1
    return {
        "top": table.head(n),
        "bottom": table.tail(n).iloc[::-1],
        "products": len(table),
        "products_for_80pct": n80,
    }


def country_performance(df, flt=None) -> pd.DataFrame:
    """Revenue, orders, units, share and revenue per order for each country."""
    t = revenue_by_country(df, flt)
    t["revenue_per_order"] = np.where(t["orders"] > 0, t["revenue"] / t["orders"].where(t["orders"] > 0, 1), 0.0)
    return t


def rfm_table(df, flt=None) -> pd.DataFrame:
    """Recency (days), frequency (orders) and monetary (spend) per identified customer (R6)."""
    d = apply_filter(df, flt)
    s = d.loc[d["is_sale"] & d["has_customer"]]
    if s.empty:
        return pd.DataFrame(columns=["recency_days", "frequency", "monetary"])
    reference = d["InvoiceDate"].max().normalize() + pd.Timedelta(days=1)
    g = s.groupby("CustomerID").agg(
        last=("InvoiceDate", "max"), frequency=("InvoiceNo", "nunique"), monetary=("LineTotal", "sum")
    )
    g["recency_days"] = (reference - g["last"].dt.normalize()).dt.days
    return g[["recency_days", "frequency", "monetary"]]


def spend_concentration(df, flt=None, top_share: float = 0.10) -> float:
    """Share of customer spend from the top `top_share` of customers (0.0 if none)."""
    spend = customer_frequency(df, flt)["spend"].sort_values(ascending=False)
    if spend.empty or spend.sum() == 0:
        return 0.0
    k = max(1, int(len(spend) * top_share))
    return float(spend.head(k).sum() / spend.sum())


def _period_table(df, flt, freq: str) -> pd.DataFrame:
    d = apply_filter(df, flt)
    if d.empty:
        return pd.DataFrame(columns=["revenue", "partial", "growth"])
    first, last = d["InvoiceDate"].min(), d["InvoiceDate"].max()
    s = d.loc[d["is_sale"]]
    periods = s["InvoiceDate"].dt.to_period(freq)
    out = s.groupby(periods)["LineTotal"].sum().to_frame("revenue").sort_index()
    out["partial"] = [
        (p.start_time.normalize() < first.normalize()) or (p.end_time.normalize() > last.normalize())
        for p in out.index
    ]
    prev = out["revenue"].shift(1)
    prev_partial = out["partial"].shift(1, fill_value=True).astype(bool)
    comparable = ~out["partial"] & ~prev_partial & (prev > 0)
    out["growth"] = np.where(comparable, out["revenue"] / prev - 1, np.nan)
    out.index = out.index.astype(str)
    return out


def monthly_trend(df, flt=None) -> pd.DataFrame:
    """Monthly gross sales with a partial flag and month-over-month growth."""
    return _period_table(df, flt, "M")


def quarterly_trend(df, flt=None) -> pd.DataFrame:
    """Quarterly gross sales with a partial flag and quarter-over-quarter growth."""
    return _period_table(df, flt, "Q")


def observations(df, names=None, flt=None) -> list[str]:
    """Sentences generated from computed values only."""
    k = compute_kpis(df, flt)
    if k.orders == 0:
        return ["No sales in the selected data."]
    out = [
        f"Gross sales are {k.gross_sales:,.2f} currency units across {k.orders:,} orders; "
        f"average order value is {k.average_order_value:,.2f}.",
        f"Returns are {abs(k.returns_value):,.2f}, or {k.return_rate:.1%} of gross sales.",
    ]
    c = country_performance(df, flt)
    if len(c) > 1:
        out.append(f"{c.index[0]} is the largest market with {c['share'].iloc[0]:.1%} of gross sales.")
    p = product_performance(df, names, flt)
    out.append(f"{p['products_for_80pct']:,} of {p['products']:,} products make up 80% of product revenue.")
    out.append(f"The top 10% of identified customers account for {spend_concentration(df, flt):.1%} of customer spend.")
    m = monthly_trend(df, flt)
    valid = m["growth"].dropna()
    if not valid.empty:
        best = valid.idxmax()
        worst = valid.idxmin()
        out.append(f"Among complete months, growth was strongest in {best} ({valid[best]:+.1%}) and weakest in {worst} ({valid[worst]:+.1%}).")
    partial = m.index[m["partial"]].tolist()
    if partial:
        out.append(f"Partial periods excluded from growth: {', '.join(partial)}.")
    return out
