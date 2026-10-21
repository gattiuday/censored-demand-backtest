"""WMAPE and the two sided score."""

from __future__ import annotations

import numpy as np
import pytest

from cdb.backtest import score, wmape
from cdb.errors import UnusableSeries
from cdb.forecast import WINDOW, forecast


def test_wmape_is_the_sum_of_errors_over_the_sum_of_actuals():
    actual = np.array([10.0, 20.0])
    predicted = np.array([12.0, 17.0])
    assert wmape(actual, predicted) == pytest.approx(5 / 30)


def test_wmape_over_all_zero_actuals_is_undefined_rather_than_zero():
    with pytest.raises(UnusableSeries, match="undefined rather than zero"):
        wmape(np.zeros(3), np.ones(3))


def test_wmape_refuses_mismatched_shapes():
    with pytest.raises(UnusableSeries, match="same shape"):
        wmape(np.ones(3), np.ones(2))


def test_a_perfect_forecast_of_demand_scores_zero_against_demand(uncensored_item):
    predictions = uncensored_item.demand[WINDOW:].astype(float)
    result = score(uncensored_item, "uncorrected", predictions)
    assert result.against_demand == pytest.approx(0.0)


def test_more_predictions_than_periods_is_refused(item):
    with pytest.raises(UnusableSeries, match="predictions for a series"):
        score(item, "uncorrected", np.zeros(item.periods + 5))


def test_the_score_carries_the_censoring_rate_of_the_window_it_scored(item):
    predictions = forecast(item, "uncorrected")
    result = score(item, "uncorrected", predictions)
    assert result.periods == item.periods - WINDOW
    assert result.censored_share == pytest.approx(float(item.censored[WINDOW:].mean()))
