"""Three ways to put a number on a censored day, and what each one assumes.

A censored day tells you demand was at least the sales figure. Every method
here turns that inequality into a point estimate, and it does so by adding an
assumption the data does not contain. The assumptions are stated rather than
buried, because the gap between them is larger than the gap between most
forecasting methods and it is the thing a reader should be checking.

None of these is a demand estimator in the statistical sense. They are the
three things planning systems actually do, and `experiments/exp03` grades them
against the planted demand so the cost of each assumption is a measurement.
"""

from __future__ import annotations

import numpy as np

from cdb.censor import Series
from cdb.errors import UnusableSeries

__all__ = [
    "CORRECTIONS",
    "correct",
    "drop_censored",
    "scale_by_availability",
    "uplift_to_clean_mean",
]


def drop_censored(series: Series) -> tuple[np.ndarray, np.ndarray]:
    """Discard the censored days. Assumes they were missing at random.

    They were not: a day is censored because demand was high relative to stock,
    so dropping them removes the upper tail of the demand distribution and the
    remaining mean is biased low. It is nonetheless the most common thing done,
    because it requires no assumption anyone has to defend in a meeting.

    Returns the retained values and the mask of what was kept, so a caller can
    see how much of the series the method threw away.
    """
    keep = ~series.censored
    if not keep.any():
        raise UnusableSeries(
            f"{series.item}: every day is censored, so dropping censored days leaves "
            "nothing; this is undefined rather than zero"
        )
    return series.sales[keep].astype(float), keep


def uplift_to_clean_mean(series: Series) -> tuple[np.ndarray, np.ndarray]:
    """Replace each censored day with the mean of the uncensored ones.

    Assumes a censored day was an average day whose sale was cut off. It
    corrects the count of days, which dropping does not, and still removes the
    tail, because an average day is by construction not a high one. Expected to
    sit between the other two and is the correction `forecast.uplifted_mean`
    applies.
    """
    clean, _ = drop_censored(series)
    filled = series.sales.astype(float).copy()
    filled[series.censored] = clean.mean()
    return filled, np.ones(series.periods, dtype=bool)


def scale_by_availability(series: Series) -> tuple[np.ndarray, np.ndarray]:
    """Scale each censored day up by how much of it had stock.

    Assumes demand arrived at a constant rate through the day and that stock ran
    out partway, so a day that sold its whole opening stock is scaled by the
    reciprocal of the share of the day that stock lasted. This repository's
    fixture has daily granularity and no intraday stock curve, so that share is
    not observable and the method is applied with the crudest available proxy:
    availability over the clean mean, capped at one. It is included because it
    is what systems with intraday data do, and because the proxy's failure is
    worth measuring rather than asserting. `docs/adr/ADR-003` is the account of
    why a method whose input this fixture cannot supply is graded here anyway.
    """
    clean, _ = drop_censored(series)
    level = clean.mean()
    if level <= 0:
        raise UnusableSeries(
            f"{series.item}: the uncensored days average zero, so there is no level to "
            "scale against"
        )
    filled = series.sales.astype(float).copy()
    share = np.clip(series.available / level, 0.05, 1.0)
    filled[series.censored] = series.sales[series.censored] / share[series.censored]
    return filled, np.ones(series.periods, dtype=bool)


#: Name to method, so experiments iterate rather than repeat.
CORRECTIONS = {
    "drop_censored": drop_censored,
    "uplift_to_clean_mean": uplift_to_clean_mean,
    "scale_by_availability": scale_by_availability,
}


def correct(series: Series, method: str) -> tuple[np.ndarray, np.ndarray]:
    if method not in CORRECTIONS:
        raise UnusableSeries(
            f"unknown correction '{method}'; expected one of {', '.join(CORRECTIONS)}"
        )
    return CORRECTIONS[method](series)
