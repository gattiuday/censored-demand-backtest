"""The two forecasters, and what separates them."""

from __future__ import annotations

import numpy as np
import pytest

from cdb.censor import Series
from cdb.errors import UnusableSeries
from cdb.forecast import WINDOW, forecast, uncorrected_mean, uplifted_mean


def _flat(sales, censored):
    values = np.array(sales)
    return Series(
        item="SKU-F",
        demand=values + np.array(censored).astype(int) * 1000,
        available=values,
        sales=values,
        censored=np.array(censored),
    )


def test_the_two_forecasters_agree_when_nothing_is_censored():
    series = _flat([10] * 40, [False] * 40)
    assert uncorrected_mean(series, 30) == pytest.approx(uplifted_mean(series, 30))


def test_the_uplift_raises_the_level_when_censored_days_sold_less():
    series = _flat([10] * 20 + [4] * 10 + [10] * 10, [False] * 20 + [True] * 10 + [False] * 10)
    assert uplifted_mean(series, 35) > uncorrected_mean(series, 35)


def test_the_uplift_falls_back_to_the_sales_mean_when_every_day_is_censored():
    """A floor, reported as one rather than passed off as a demand estimate."""
    series = _flat([4] * 40, [True] * 40)
    assert uplifted_mean(series, 35) == pytest.approx(uncorrected_mean(series, 35))


def test_the_first_period_falls_back_to_the_first_observation():
    series = _flat([7] * 40, [False] * 40)
    assert uncorrected_mean(series, 0) == pytest.approx(7.0)
    assert uplifted_mean(series, 0) == pytest.approx(7.0)


def test_an_unknown_forecaster_is_refused_by_name(item):
    with pytest.raises(UnusableSeries, match="unknown forecaster"):
        forecast(item, "ets")


def test_a_backtest_with_no_periods_to_score_is_refused(item):
    with pytest.raises(UnusableSeries, match="leaves no periods to score"):
        forecast(item, "uncorrected", start=item.periods)


def test_the_forecast_covers_every_period_after_the_window(item):
    assert len(forecast(item, "uncorrected")) == item.periods - WINDOW
