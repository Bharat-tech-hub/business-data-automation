"""Business KPIs under BUSINESS_RULES R9. Input: the cleaned DataFrame from clean().

Sale rows are is_sale (R1); return rows are is_cancelled (R2). Orders are distinct
InvoiceNo, never lines. Returns are not linked to original sales (R10), so the
return rate is a ratio of totals.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class KpiFilter:
    """Optional filters. end_date is inclusive of the whole day."""

    start_date: pd.Timestamp | str | None = None
    end_date: pd.Timestamp | str | None = None
    countries: tuple[str, ...] = field(default_factory=tuple)


def apply_filter(df: pd.DataFrame, flt: KpiFilter | None = None) -> pd.DataFrame:
    """Return the rows matching the filter (the input is not modified)."""
    if flt is None:
        return df
    mask = pd.Series(True, index=df.index)
    if flt.start_date is not None:
        mask &= df["InvoiceDate"] >= pd.Timestamp(flt.start_date)
    if flt.end_date is not None:
        mask &= df["InvoiceDate"] < pd.Timestamp(flt.end_date).normalize() + pd.Timedelta(days=1)
    if flt.countries:
        mask &= df["Country"].isin(list(flt.countries))
    return df.loc[mask]


@dataclass(frozen=True)
class KpiSummary:
    """Headline metrics. Amounts are in currency units."""

    gross_sales: float
    returns_value: float  # negative or zero
    net_revenue: float
    orders: int
    units_sold: int
    average_order_value: float
    average_selling_price: float
    return_rate: float  # |returns| / gross sales
    shipping_and_fees: float  # R5, reported separately


def _safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b else 0.0


def _sales(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df["is_sale"]]


def compute_kpis(df: pd.DataFrame, flt: KpiFilter | None = None) -> KpiSummary:
    """Compute the headline KPIs for the (optionally filtered) data."""
    d = apply_filter(df, flt)
    sales = _sales(d)
    gross = float(sales["LineTotal"].sum())
    returns = float(d.loc[d["is_cancelled"], "LineTotal"].sum())
    orders = int(sales["InvoiceNo"].nunique())
    units = int(sales["Quantity"].sum())
    fee_mask = ~d["is_product"] & ~d["is_cancelled"] & (d["Quantity"] > 0) & (d["UnitPrice"] > 0)
    return KpiSummary(
        gross_sales=gross,
        returns_value=returns,
        net_revenue=gross + returns,
        orders=orders,
        units_sold=units,
        average_order_value=_safe_div(gross, orders),
        average_selling_price=_safe_div(gross, units),
        return_rate=_safe_div(abs(returns), gross),
        shipping_and_fees=float(d.loc[fee_mask, "LineTotal"].sum()),
    )


def revenue_by_country(df: pd.DataFrame, flt: KpiFilter | None = None) -> pd.DataFrame:
    """Revenue, orders, units and share per country, largest first."""
    s = _sales(apply_filter(df, flt))
    out = s.groupby("Country").agg(
        revenue=("LineTotal", "sum"), orders=("InvoiceNo", "nunique"), units=("Quantity", "sum")
    )
    total = out["revenue"].sum()
    out["share"] = out["revenue"] / total if total else 0.0
    return out.sort_values("revenue", ascending=False)


def revenue_by_product(
    df: pd.DataFrame, names: pd.Series | None = None, flt: KpiFilter | None = None
) -> pd.DataFrame:
    """Revenue, units, orders, share and cumulative share per StockCode (no categories exist)."""
    s = _sales(apply_filter(df, flt))
    out = s.groupby("StockCode").agg(
        revenue=("LineTotal", "sum"), units=("Quantity", "sum"), orders=("InvoiceNo", "nunique")
    )
    out = out.sort_values("revenue", ascending=False)
    total = out["revenue"].sum()
    out["share"] = out["revenue"] / total if total else 0.0
    out["cumulative_share"] = out["share"].cumsum()
    if names is not None:
        out.insert(0, "name", [names.get(c, "(no description)") for c in out.index])
    return out


def monthly_revenue(df: pd.DataFrame, flt: KpiFilter | None = None) -> pd.DataFrame:
    """Gross sales, returns and net revenue per InvoiceMonth (returns by cancellation month, R10)."""
    d = apply_filter(df, flt)
    gross = _sales(d).groupby("InvoiceMonth")["LineTotal"].sum().rename("gross_sales")
    returns = d.loc[d["is_cancelled"]].groupby("InvoiceMonth")["LineTotal"].sum().rename("returns")
    out = pd.concat([gross, returns], axis=1).fillna(0.0).sort_index()
    out["net_revenue"] = out["gross_sales"] + out["returns"]
    return out


def customer_frequency(df: pd.DataFrame, flt: KpiFilter | None = None) -> pd.DataFrame:
    """Orders and spend per customer, over sale rows with a CustomerID (R6)."""
    s = _sales(apply_filter(df, flt))
    s = s.loc[s["has_customer"]]
    return s.groupby("CustomerID").agg(orders=("InvoiceNo", "nunique"), spend=("LineTotal", "sum"))


def repeat_customer_share(df: pd.DataFrame, flt: KpiFilter | None = None) -> float:
    """Share of identified customers with more than one order (0.0 if none)."""
    freq = customer_frequency(df, flt)
    return float((freq["orders"] > 1).mean()) if len(freq) else 0.0
