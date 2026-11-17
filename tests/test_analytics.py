"""Tests for src.analytics (hand-built data, values checkable by hand)."""

import pandas as pd
import pytest

from src.analytics import (
    country_performance,
    monthly_trend,
    observations,
    product_performance,
    quarterly_trend,
    rfm_table,
    spend_concentration,
)
from src.cleaning import clean
from src.kpis import KpiFilter
from src.schema import REQUIRED_COLUMNS


def make_df() -> pd.DataFrame:
    # NOTE: stock codes must not be R5 non-product codes (so not "B", "D", "M", ...).
    rows = [
        ["1", "A1", "ITEM A", 1, "2011-01-01 09:00:00", 100.0, 1, "United Kingdom"],
        ["2", "A1", "ITEM A", 1, "2011-02-10 09:00:00", 50.0, 1, "United Kingdom"],
        ["3", "P2", "ITEM P", 1, "2011-02-11 09:00:00", 50.0, 2, "France"],
        ["4", "P2", "ITEM P", 2, "2011-03-12 09:00:00", 100.0, 2, "France"],
        ["5", "C1", "ITEM C", 1, "2011-04-15 09:00:00", 40.0, 3, "United Kingdom"],
    ]
    cleaned, _ = clean(pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS)))
    return cleaned


def test_fixture_rows_are_all_sales():
    assert make_df()["is_sale"].all()


def test_monthly_growth_and_partial_flags():
    m = monthly_trend(make_df())
    assert m["revenue"].tolist() == pytest.approx([100.0, 100.0, 200.0, 40.0])
    assert m["partial"].tolist() == [False, False, False, True]
    assert pd.isna(m.loc["2011-01", "growth"])
    assert m.loc["2011-02", "growth"] == pytest.approx(0.0)
    assert m.loc["2011-03", "growth"] == pytest.approx(1.0)
    assert pd.isna(m.loc["2011-04", "growth"])


def test_quarterly_marks_partial_and_no_growth():
    q = quarterly_trend(make_df())
    assert q.index.tolist() == ["2011Q1", "2011Q2"]
    assert q.loc["2011Q1", "revenue"] == pytest.approx(400.0)
    assert q.loc["2011Q2", "revenue"] == pytest.approx(40.0)
    assert q["partial"].tolist() == [False, True]
    assert q["growth"].isna().all()


def test_product_performance():
    p = product_performance(make_df(), n=2)
    assert p["products"] == 3
    assert p["top"].index.tolist() == ["P2", "A1"]
    assert p["bottom"].index.tolist() == ["C1", "A1"]
    assert p["products_for_80pct"] == 2  # 250/440 = 0.57, then 400/440 = 0.91


def test_country_performance_revenue_per_order():
    c = country_performance(make_df())
    assert c.loc["France", "revenue_per_order"] == pytest.approx(125.0)
    assert c.loc["United Kingdom", "revenue_per_order"] == pytest.approx(190.0 / 3)


def test_rfm_table_values():
    r = rfm_table(make_df())
    # reference day = 2011-04-16; customer 1 last ordered 2011-02-10 -> 65 days
    assert r.loc["1", "recency_days"] == 65
    assert r.loc["1", "frequency"] == 2
    assert r.loc["1", "monetary"] == pytest.approx(150.0)
    assert r.loc["3", "recency_days"] == 1


def test_spend_concentration():
    # spends: 1=150, 2=250, 3=40; top 10% of 3 customers = 1 customer
    assert spend_concentration(make_df()) == pytest.approx(250.0 / 440.0)


def test_empty_selection():
    flt = KpiFilter(countries=("Nowhere",))
    assert monthly_trend(make_df(), flt).empty
    assert rfm_table(make_df(), flt).empty
    assert spend_concentration(make_df(), flt) == 0.0
    assert observations(make_df(), flt=flt) == ["No sales in the selected data."]


def test_observations_are_computed():
    obs = observations(make_df())
    assert any("440.00" in line for line in obs)
    assert any("largest market" in line for line in obs)
    assert any("2011-04" in line and "Partial" in line for line in obs)


def test_observations_skip_largest_market_for_single_country():
    df = make_df()
    france_only = df[df["Country"] == "France"]
    assert not any("largest market" in line for line in observations(france_only))
    assert any("largest market" in line for line in observations(df))

