"""Scoring a forecast, against sales and against demand, and the gap between.

The two scores are the whole repository. A backtest run on a sales history
scores a forecast against `sales`, because that is the column the history has.
What the forecast is for is demand. On an uncensored day those agree and on a
censored day they do not, so the score a team reads is a score against a
different quantity from the one they are trying to predict.

`against_demand` exists only because this repository's fixtures are generated.
It is the counterfactual score, and a real backtest cannot compute it. Every
figure here that compares the two is a statement about how far wrong the
computable one is, measured on a case where the uncomputable one is known.
"""

from __future__ import annotations

import numpy as np

from cdb.censor import Series
from cdb.errors import UnusableSeries

__all__ = ["Score", "score", "wmape"]

from dataclasses import dataclass


def wmape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Weighted mean absolute percentage error: sum of errors over sum of actuals.

    Weighted rather than the mean of per period percentages, because a period
    with an actual of zero has no percentage and the mean of percentages is
    dominated by the smallest actuals. The denominator is the quantity being
    predicted, which is the choice that matters here: scored against sales it is
    the sum of sales, and the censoring makes that sum smaller than the sum of
    demand, so the same absolute error reads as a larger percentage.
    """
    if actual.shape != predicted.shape:
        raise UnusableSeries(
            f"actual and predicted must have the same shape, got {actual.shape} "
            f"and {predicted.shape}"
        )
    total = float(np.abs(actual).sum())
    if total == 0:
        raise UnusableSeries(
            "every actual in this window is zero, so WMAPE is undefined rather than zero"
        )
    return float(np.abs(actual - predicted).sum() / total)


@dataclass(frozen=True)
class Score:
    """One forecaster on one series, scored both ways."""

    item: str
    forecaster: str
    against_sales: float
    against_demand: float
    censored_share: float
    periods: int

    @property
    def score_gap(self) -> float:
        """Demand score minus sales score, in WMAPE points. Measured negative.

        This property was called `understatement`, which assumed its own answer.
        Scoring against sales compares the forecast to a smaller number on a
        censored day, which raises the numerator, and divides by a smaller
        total, which raises the percentage again; both run the same way, so the
        computable score is the pessimistic one. On this fixture the gap is
        negative at every level of cover.

        That is worse than a flattering bias rather than better. A number that
        says accuracy is poor invites no investigation of the measurement, and
        the ranking it produces is still wrong, which is exp01.
        """
        return (self.against_demand - self.against_sales) * 100


def score(series: Series, forecaster: str, predictions: np.ndarray) -> Score:
    """Score one forecaster against both columns over the backtest window."""
    start = series.periods - len(predictions)
    if start < 0:
        raise UnusableSeries(
            f"{series.item}: {len(predictions)} predictions for a series of {series.periods}"
        )
    return Score(
        item=series.item,
        forecaster=forecaster,
        against_sales=wmape(series.sales[start:], predictions),
        against_demand=wmape(series.demand[start:], predictions),
        censored_share=float(series.censored[start:].mean()),
        periods=len(predictions),
    )
