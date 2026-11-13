"""Tests for src.visualization: figure types, titles and element counts, not pixels."""

import plotly.graph_objects as go
from matplotlib.figure import Figure

from src import visualization as v
from src.kpis import KpiFilter
from tests.test_analytics import make_df

NOWHERE = KpiFilter(countries=("Nowhere",))


def test_static_monthly_has_one_bar_per_month():
    fig = v.static_monthly_revenue(make_df())
    assert isinstance(fig, Figure)
    assert len(fig.axes[0].patches) == 4
    assert "Monthly" in fig.axes[0].get_title()


def test_static_monthly_responds_to_filter():
    fig = v.static_monthly_revenue(make_df(), KpiFilter(countries=("France",)))
    assert len(fig.axes[0].patches) == 2  # Feb and Mar


def test_static_top_products_counts():
    assert len(v.static_top_products(make_df()).axes[0].patches) == 3
    assert len(v.static_top_products(make_df(), n=2).axes[0].patches) == 2


def test_static_country_and_exclude_top():
    assert len(v.static_country_revenue(make_df()).axes[0].patches) == 2
    assert len(v.static_country_revenue(make_df(), exclude_top=True).axes[0].patches) == 1


def test_static_weekday_hour_has_two_axes():
    fig = v.static_weekday_hour(make_df())
    assert len(fig.axes) == 2
    assert len(fig.axes[0].patches) == 7
    assert len(fig.axes[1].patches) == 24


def test_static_customer_spend_log_axis():
    ax = v.static_customer_spend(make_df()).axes[0]
    assert ax.get_xscale() == "log"
    assert len(ax.patches) > 0


def test_static_rfm_has_one_point_per_customer():
    ax = v.static_rfm(make_df()).axes[0]
    assert len(ax.collections[0].get_offsets()) == 3


def test_static_empty_data_gives_no_data_figure():
    for func in (v.static_monthly_revenue, v.static_top_products, v.static_country_revenue,
                 v.static_weekday_hour, v.static_customer_spend, v.static_rfm):
        fig = func(make_df(), flt=NOWHERE)
        assert isinstance(fig, Figure)
        assert v.NO_DATA in fig.axes[0].texts[0].get_text()


def test_interactive_monthly_marks_partial_month():
    fig = v.interactive_monthly_revenue(make_df())
    assert isinstance(fig, go.Figure)
    assert len(fig.data[0].x) == 4
    colors = list(fig.data[0].marker.color)
    assert colors[-1] == v.PARTIAL_COLOR and colors[0] == v.MAIN_COLOR


def test_interactive_products_countries_rfm_weekday():
    assert len(v.interactive_top_products(make_df()).data[0].x) == 3
    assert len(v.interactive_country_revenue(make_df()).data[0].x) == 2
    assert len(v.interactive_country_revenue(make_df(), exclude_top=True).data[0].x) == 1
    assert len(v.interactive_rfm(make_df()).data[0].x) == 3
    fig = v.interactive_weekday_hour(make_df())
    assert (len(fig.data[0].x), len(fig.data[1].x)) == (7, 24)


def test_interactive_empty_data_gives_no_data_figure():
    for func in (v.interactive_monthly_revenue, v.interactive_top_products, v.interactive_country_revenue,
                 v.interactive_weekday_hour, v.interactive_rfm):
        fig = func(make_df(), flt=NOWHERE)
        assert isinstance(fig, go.Figure)
        assert v.NO_DATA in fig.layout.annotations[0].text
