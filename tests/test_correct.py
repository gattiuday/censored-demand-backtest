"""The three corrections and the assumption each one makes."""

from __future__ import annotations

import numpy as np
import pytest

from cdb.censor import Series
from cdb.correct import CORRECTIONS, correct, drop_censored
from cdb.errors import UnusableSeries


def _series(sales, censored, available=None):
    values = np.array(sales)
    flags = np.array(censored)
    return Series(
        item="SKU-C",
        demand=values + flags.astype(int) * 50,
        available=np.array(available) if available is not None else values,
        sales=values,
        censored=flags,
    )


def test_dropping_keeps_only_the_uncensored_days():
    series = _series([10, 4, 10], [False, True, False])
    kept, mask = drop_censored(series)
    assert list(kept) == [10.0, 10.0]
    assert list(mask) == [True, False, True]


def test_dropping_a_fully_censored_series_is_undefined_rather_than_zero():
    series = _series([4, 4], [True, True])
    with pytest.raises(UnusableSeries, match="undefined rather than zero"):
        drop_censored(series)


def test_the_uplift_fills_censored_days_with_the_clean_mean():
    series = _series([10, 4, 12], [False, True, False])
    filled, mask = correct(series, "uplift_to_clean_mean")
    assert filled[1] == pytest.approx(11.0)
    assert mask.all()


def test_scaling_by_availability_raises_a_censored_day():
    series = _series([10, 5, 12], [False, True, False], available=[40, 5, 40])
    filled, _ = correct(series, "scale_by_availability")
    assert filled[1] > series.sales[1]


def test_scaling_refuses_a_series_whose_clean_days_average_zero():
    series = _series([0, 4, 0], [False, True, False], available=[0, 4, 0])
    with pytest.raises(UnusableSeries, match="no level to"):
        correct(series, "scale_by_availability")


def test_an_unknown_correction_is_refused_by_name(item):
    with pytest.raises(UnusableSeries, match="unknown correction"):
        correct(item, "kaplan_meier")


@pytest.mark.parametrize("method", list(CORRECTIONS))
def test_every_correction_raises_the_estimated_total(method, heavy_panel):
    """A method that lowered it would not be a correction."""
    for series in heavy_panel[:5]:
        values, _ = correct(series, method)
        assert float(values.mean()) * series.periods >= float(series.sales.sum()) - 1e-9
