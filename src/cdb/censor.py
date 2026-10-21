"""What a sales number is, as opposed to what it is read as.

A sales history records transactions. Demand is what customers wanted. On a day
with stock these are the same number, which is why the distinction survives so
long unexamined, and on a day without stock they are not:

    sales = min(demand, stock available that day)

The second term is the censoring. It is not noise and it does not average out:
it is one sided, it is correlated with high demand, and it is produced by the
very policy whose performance the sales history is being used to judge.

Nothing in this module estimates demand. A censored day tells you demand was at
least the sales figure and nothing more, so a point estimate of it requires an
assumption from outside the data. `correct.py` holds three such assumptions and
`experiments/exp03` grades them against the planted truth. The purpose of this
module is to keep the two quantities apart in the type system, so that a
function that takes sales cannot be handed demand by accident.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cdb.errors import UnusableSeries

__all__ = ["Series", "censor", "fill_rate"]


@dataclass(frozen=True)
class Series:
    """One item's history: what was wanted, what was available, what was sold.

    `demand` is present here because this package's fixtures are generated, and
    it is the only reason any of the figures in this repository can be checked.
    A real sales export has `sales` and `censored` at best, and usually only
    `sales`. Every function that is allowed to see `demand` is in this module,
    the generator, or an experiment; nothing in `backtest.py` or `correct.py`
    reads it, and a test asserts that.
    """

    item: str
    demand: np.ndarray
    available: np.ndarray
    sales: np.ndarray
    censored: np.ndarray

    def __post_init__(self) -> None:
        lengths = {len(self.demand), len(self.available), len(self.sales), len(self.censored)}
        if len(lengths) != 1:
            raise UnusableSeries(
                f"{self.item}: demand, available, sales and censored must be the same length, "
                f"got lengths {sorted(lengths)}"
            )
        if len(self.demand) == 0:
            raise UnusableSeries(f"{self.item}: an empty series cannot be backtested")
        if np.any(self.sales > self.demand):
            raise UnusableSeries(
                f"{self.item}: sales exceed demand on some day, which the censoring "
                "mechanism cannot produce"
            )

    @property
    def periods(self) -> int:
        return len(self.demand)

    @property
    def censored_share(self) -> float:
        """Share of days on which the sales figure is a floor and not the demand."""
        return float(self.censored.mean())

    @property
    def lost_units(self) -> int:
        """Demand that was never recorded anywhere. The quantity at issue."""
        return int((self.demand - self.sales).sum())


def censor(demand: np.ndarray, available: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply the mechanism, returning sales and the censoring flag.

    A day is censored when availability bound the sale, which is `available <
    demand` and not `sales == available`: those differ exactly when demand
    equals availability, where the sale was not actually constrained and
    counting it as censored inflates every rate computed from the flag. The
    distinction is invisible without the demand column, which is the point of
    this repository.
    """
    if demand.shape != available.shape:
        raise UnusableSeries(
            f"demand and availability must have the same shape, got {demand.shape} "
            f"and {available.shape}"
        )
    if np.any(demand < 0) or np.any(available < 0):
        raise UnusableSeries("demand and availability cannot be negative")
    sales = np.minimum(demand, available)
    return sales, available < demand


def fill_rate(series: Series) -> float:
    """Units sold over units demanded, which is what the censoring costs."""
    demanded = series.demand.sum()
    if demanded == 0:
        raise UnusableSeries(
            f"{series.item}: no demand in the period, so the fill rate is undefined "
            "rather than perfect"
        )
    return float(series.sales.sum() / demanded)
