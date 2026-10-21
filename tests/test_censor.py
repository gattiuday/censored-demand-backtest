"""The censoring mechanism and the invariants on a series."""

from __future__ import annotations

import numpy as np
import pytest

from cdb.censor import Series, censor, fill_rate
from cdb.errors import UnusableSeries


def _series(demand, available, item="SKU-X"):
    sales, flags = censor(np.array(demand), np.array(available))
    return Series(
        item=item,
        demand=np.array(demand),
        available=np.array(available),
        sales=sales,
        censored=flags,
    )


def test_a_day_with_stock_records_the_demand():
    series = _series([5, 7], [100, 100])
    assert list(series.sales) == [5, 7]
    assert not series.censored.any()
    assert series.lost_units == 0


def test_a_day_without_stock_records_the_stock():
    series = _series([10], [4])
    assert list(series.sales) == [4]
    assert series.censored.all()
    assert series.lost_units == 6


def test_demand_exactly_equal_to_availability_is_not_censored():
    """Nothing was turned away, so counting it censored inflates every rate."""
    series = _series([6], [6])
    assert list(series.sales) == [6]
    assert not series.censored.any()
    assert series.lost_units == 0


def test_mismatched_shapes_are_refused():
    with pytest.raises(UnusableSeries, match="same shape"):
        censor(np.array([1, 2]), np.array([1]))


def test_negative_inputs_are_refused():
    with pytest.raises(UnusableSeries, match="cannot be negative"):
        censor(np.array([-1]), np.array([1]))


def test_a_series_whose_columns_disagree_in_length_is_refused():
    with pytest.raises(UnusableSeries, match="same length"):
        Series(
            item="SKU-X",
            demand=np.array([1, 2]),
            available=np.array([1, 2]),
            sales=np.array([1]),
            censored=np.array([False, False]),
        )


def test_an_empty_series_is_refused():
    with pytest.raises(UnusableSeries, match="empty series"):
        Series(
            item="SKU-X",
            demand=np.array([], dtype=int),
            available=np.array([], dtype=int),
            sales=np.array([], dtype=int),
            censored=np.array([], dtype=bool),
        )


def test_sales_above_demand_are_refused_because_the_mechanism_cannot_produce_them():
    with pytest.raises(UnusableSeries, match="cannot produce"):
        Series(
            item="SKU-X",
            demand=np.array([1]),
            available=np.array([5]),
            sales=np.array([5]),
            censored=np.array([False]),
        )


def test_a_fill_rate_over_no_demand_is_undefined_rather_than_perfect():
    series = _series([0, 0], [10, 10])
    with pytest.raises(UnusableSeries, match="undefined rather than perfect"):
        fill_rate(series)


def test_the_fill_rate_is_units_sold_over_units_wanted():
    series = _series([10, 10], [10, 5])
    assert fill_rate(series) == pytest.approx(15 / 20)


def test_a_series_shorter_than_four_review_cycles_is_refused():
    """The censoring rate over a window that short is a property of the window."""
    from cdb.generator import generate_item

    with pytest.raises(UnusableSeries, match="artefact of the window"):
        generate_item("SKU-SHORT", periods=14)
