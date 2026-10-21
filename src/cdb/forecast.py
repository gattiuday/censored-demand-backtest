"""Two forecasters that differ only in whether they correct for censoring.

The point of the pair is the comparison, so they share a method. Both take a
trailing window of the sales history and average it; one uses the sales figures
as they stand and the other replaces the censored ones with an estimate of what
demand was. Everything else is identical, which means any difference between
them in a backtest is attributable to the correction and nothing else.

Neither reads the demand column. The corrected one uses the censoring flag,
which a real system does have whenever it records stock on hand, and that is the
whole of the extra information it needs.
"""

from __future__ import annotations

import numpy as np

from cdb.censor import Series
from cdb.errors import UnusableSeries

__all__ = ["FORECASTERS", "forecast", "uncorrected_mean", "uplifted_mean"]

#: Days of history each forecaster averages over. Four weeks, so the weekly
#: cycle in the fixture contributes whole periods and the comparison is not
#: confounded by a window that cuts a week in half.
WINDOW = 28


def _window(values: np.ndarray, index: int) -> np.ndarray:
    return values[max(0, index - WINDOW) : index]


def uncorrected_mean(series: Series, index: int) -> float:
    """The trailing mean of sales, which is what a planner reads off the system."""
    window = _window(series.sales, index)
    return float(window.mean()) if len(window) else float(series.sales[0])


def uplifted_mean(series: Series, index: int) -> float:
    """The trailing mean with censored days replaced by an uplift.

    The uplift is the mean of the uncensored days in the same window, which
    treats a censored day as an ordinary day whose sale happened to be cut off.
    That is the simplest assumption available and it is the one most planning
    systems make when they make any; `correct.py` holds two others and
    `experiments/exp03` grades all three. The assumption is doing real work and
    the repository's claim is about the comparison, not about this estimator.
    """
    sales = _window(series.sales, index)
    censored = _window(series.censored, index)
    if len(sales) == 0:
        return float(series.sales[0])
    clean = sales[~censored]
    if len(clean) == 0:
        # Every day in the window was censored, so there is no uncensored day to
        # learn a level from. Returning the sales mean is a floor and is
        # reported as such rather than silently passed off as a demand estimate.
        return float(sales.mean())
    replaced = np.where(censored, clean.mean(), sales)
    return float(replaced.mean())


#: Name to function. Kept as a mapping so experiments iterate over it rather
#: than repeating the pair, and so adding a third forecaster cannot be done
#: without it appearing in every figure.
FORECASTERS = {
    "uncorrected": uncorrected_mean,
    "uplifted": uplifted_mean,
}


def forecast(series: Series, name: str, start: int = WINDOW) -> np.ndarray:
    """One step ahead forecasts from `start` to the end of the series."""
    if name not in FORECASTERS:
        raise UnusableSeries(
            f"unknown forecaster '{name}'; expected one of {', '.join(FORECASTERS)}"
        )
    if start >= series.periods:
        raise UnusableSeries(
            f"{series.item}: a backtest starting at {start} leaves no periods to score "
            f"in a series of {series.periods}"
        )
    method = FORECASTERS[name]
    return np.array([method(series, index) for index in range(start, series.periods)])
