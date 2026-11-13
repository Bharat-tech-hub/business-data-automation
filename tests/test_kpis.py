"""Tests for src.kpis using a hand-built frame (expected values checkable by hand)."""

import pandas as pd
import pytest

from src.cleaning import clean
from src.kpis import (
    KpiFilter,
    apply_filter,
    compute_kpis,
    customer_frequency,
    monthly_revenue,
    repeat_customer_share,
    revenue_by_country,
    revenue_by_product,
)
from src.schema import REQUIRED_COLUMNS


def make_df() -> pd.DataFrame:
    rows = [
        ["1", "A1", "ITEM A", 2, "2011-01-10 10:00:00", 10.00, 1, "United Kingdom"],
        ["1", "B1", "ITEM B", 1, "2011-01-10 10:00:00", 5.00, 1, "United Kingdom"],
        ["2", "A1", "ITEM A", 4, "2011-02-15 11:00:00", 2.50, 1, "United Kingdom"],
        ["3", "C1", "ITEM C", 1, "2011-02-20 12:00:00", 100.00, 2, "France"],
        ["C4", "A1", "ITEM A", -1, "2011-02-21 09:00:00", 10.00, 1, "United Kingdom"],
        ["5", "POST", "POSTAGE", 1, "2011-02-20 12:00:00", 8.00, 2, "France"],
        ["6", "A1", "ITEM A", 3, "2011-02-22 09:00:00", 0.00, None, "United Kingdom"],
    ]
    cleaned, _ = clean(pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS)))
    return cleaned


def test_headline_kpis():
    k = compute_kpis(make_df())
    assert k.gross_sales == pytest.approx(135.00)
    assert k.returns_value == pytest.approx(-10.00)
    assert k.net_revenue == pytest.approx(125.00)
    assert k.orders == 3
    assert k.units_sold == 8  # 2 + 1 + 4 + 1
    assert k.average_order_value == pytest.approx(45.00)
    assert k.average_selling_price == pytest.approx(135.00 / 8)
    assert k.return_rate == pytest.approx(10.00 / 135.00)
    assert k.shipping_and_fees == pytest.approx(8.00)


def test_orders_count_invoices_not_lines():
    assert compute_kpis(make_df()).orders == 3  # invoice 1 has two lines


def test_filter_by_country():
    k = compute_kpis(make_df(), KpiFilter(countries=("France",)))
    assert k.gross_sales == pytest.approx(100.00)
    assert k.orders == 1
    assert k.returns_value == 0.0


def test_filter_dates_end_inclusive_whole_day():
    flt = KpiFilter(start_date="2011-02-01", end_date="2011-02-20")
    k = compute_kpis(make_df(), flt)
    assert k.gross_sales == pytest.approx(110.00)  # invoice 2 (10) + invoice 3 (100)
    assert k.orders == 2


def test_empty_selection_returns_zeros():
    k = compute_kpis(make_df(), KpiFilter(countries=("Nowhere",)))
    assert (k.gross_sales, k.orders, k.units_sold) == (0.0, 0, 0)
    assert k.average_order_value == 0.0
    assert k.average_selling_price == 0.0
    assert k.return_rate == 0.0


def test_revenue_by_country():
    t = revenue_by_country(make_df())
    assert t.index.tolist() == ["France", "United Kingdom"]
    assert t.loc["France", "revenue"] == pytest.approx(100.00)
    assert t.loc["United Kingdom", "revenue"] == pytest.approx(35.00)
    assert t.loc["United Kingdom", "orders"] == 2
    assert t["share"].sum() == pytest.approx(1.0)


def test_revenue_by_product_excludes_fees_and_has_names():
    names = pd.Series({"C1": "ITEM C"})
    t = revenue_by_product(make_df(), names)
    assert "POST" not in t.index
    assert t.index.tolist() == ["C1", "A1", "B1"]
    assert t.loc["A1", "revenue"] == pytest.approx(30.00)  # 20 + 10; return not included
    assert t.loc["B1", "name"] == "(no description)"
    assert t.loc["C1", "name"] == "ITEM C"
    assert t["cumulative_share"].iloc[-1] == pytest.approx(1.0)


def test_monthly_revenue_attributes_returns_to_cancellation_month():
    t = monthly_revenue(make_df())
    assert t.loc["2011-01", "gross_sales"] == pytest.approx(25.00)
    assert t.loc["2011-02", "gross_sales"] == pytest.approx(110.00)
    assert t.loc["2011-02", "returns"] == pytest.approx(-10.00)
    assert t.loc["2011-02", "net_revenue"] == pytest.approx(100.00)
    assert t.loc["2011-01", "returns"] == 0.0


def test_customer_frequency_and_repeat_share():
    f = customer_frequency(make_df())
    assert f.loc["1", "orders"] == 2
    assert f.loc["1", "spend"] == pytest.approx(35.00)
    assert f.loc["2", "orders"] == 1
    assert repeat_customer_share(make_df()) == pytest.approx(0.5)


def test_repeat_share_empty_is_zero():
    assert repeat_customer_share(make_df(), KpiFilter(countries=("Nowhere",))) == 0.0


def test_apply_filter_none_returns_input_unchanged():
    df = make_df()
    assert apply_filter(df, None) is df
