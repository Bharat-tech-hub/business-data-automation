import pandas as pd
import plotly.graph_objects as go
import pytest
from matplotlib.figure import Figure

from src import analytics, kpis, visualization
from src.cleaning import clean
from src.kpis import KpiFilter
from src.schema import REQUIRED_COLUMNS

EMPTY = KpiFilter(start_date="2100-01-01")


def make_df() -> pd.DataFrame:
    rows = [
        ["1", "A1", "ITEM A", 1, "2011-01-01 09:00:00", 100.0, 1, "United Kingdom"],
        ["2", "A1", "ITEM A", 1, "2011-02-10 09:00:00", 50.0, 1, "United Kingdom"],
        ["3", "P2", "ITEM P", 1, "2011-02-11 09:00:00", 50.0, 2, "France"],
        ["4", "P2", "ITEM P", 2, "2011-03-12 09:00:00", 100.0, 2, "France"],
        ["5", "C1", "ITEM C", 1, "2011-04-15 09:00:00", 40.0, 3, "United Kingdom"],
    ]
    cleaned, _ = clean(pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS)))
    return cleaned


DATA_FUNCS = [
    analytics.product_performance,
    analytics.country_performance,
    analytics.rfm_table,
    analytics.spend_concentration,
    analytics.monthly_trend,
    analytics.quarterly_trend,
    kpis.revenue_by_country,
    kpis.revenue_by_product,
    kpis.monthly_revenue,
    kpis.customer_frequency,
    kpis.repeat_customer_share,
]

STATIC_CHARTS = [
    visualization.static_monthly_revenue,
    visualization.static_top_products,
    visualization.static_country_revenue,
    visualization.static_weekday_hour,
    visualization.static_customer_spend,
    visualization.static_rfm,
]

INTERACTIVE_CHARTS = [
    visualization.interactive_monthly_revenue,
    visualization.interactive_top_products,
    visualization.interactive_country_revenue,
    visualization.interactive_weekday_hour,
    visualization.interactive_rfm,
]

@pytest.mark.parametrize("fn", DATA_FUNCS, ids=lambda f: f.__name__)
def test_data_functions_survive_empty_selection(fn):
    fn(make_df(), flt=EMPTY)


@pytest.mark.parametrize("fn", STATIC_CHARTS, ids=lambda f: f.__name__)
def test_static_charts_survive_empty_selection(fn):
    assert isinstance(fn(make_df(), flt=EMPTY), Figure)


@pytest.mark.parametrize("fn", INTERACTIVE_CHARTS, ids=lambda f: f.__name__)
def test_interactive_charts_survive_empty_selection(fn):
    assert isinstance(fn(make_df(), flt=EMPTY), go.Figure)


def test_empty_selection_has_zero_orders():
    assert kpis.compute_kpis(make_df(), flt=EMPTY).orders == 0


def test_empty_selection_observation_message():
    assert analytics.observations(make_df(), flt=EMPTY) == ["No sales in the selected data."]
