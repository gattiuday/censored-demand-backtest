"""An item history with the demand written down, so the backtest can be graded.

Everything this repository claims rests on knowing what demand was, which no
sales export contains. So demand is planted: drawn first, then run through an
inventory policy that sometimes cannot meet it, and the sales column is what
that policy left behind. The planted demand is returned alongside and is never
read by `backtest.py` or `correct.py`.

The inventory process is deliberately ordinary. An order up to policy on a
weekly review, a lead time, and a target the caller sets; nothing adversarial.
The censoring this produces is the censoring a competent operation produces,
which is the case worth measuring. A pathological policy would make the finding
larger and less interesting.
"""

from __future__ import annotations

import numpy as np

from cdb.censor import Series, censor
from cdb.errors import UnusableSeries

__all__ = ["DEFAULT_SEED", "generate_item", "generate_panel"]

#: Fixed so the committed fixture regenerates byte for byte in CI.
DEFAULT_SEED = 20261021

#: Review period in days. A weekly review is what a packaged goods planner runs.
REVIEW_DAYS = 7

#: Days between placing an order and receiving it.
LEAD_DAYS = 3


def generate_item(
    item: str,
    periods: int = 364,
    base: float = 40.0,
    seasonal_amplitude: float = 0.35,
    noise: float = 0.25,
    cover_days: float = 12.0,
    seed: int = DEFAULT_SEED,
) -> Series:
    """One item: demand, the stock an order up to policy held, and the sales.

    `cover_days` is the order up to level expressed in days of average demand.
    It is the dial that sets how much censoring there is, and it is a policy
    decision rather than a property of the data, which is why the headline
    figures in this repository are reported as a function of it.
    """
    if periods < REVIEW_DAYS * 4:
        raise UnusableSeries(
            f"{item}: {periods} periods is too short to contain four review cycles, so the "
            "censoring rate it produces is an artefact of the window"
        )
    rng = np.random.default_rng(seed)
    day = np.arange(periods)
    seasonal = 1.0 + seasonal_amplitude * np.sin(2 * np.pi * day / 364.0)
    weekly = 1.0 + 0.2 * np.sin(2 * np.pi * day / 7.0)
    mean = base * seasonal * weekly
    demand = rng.poisson(np.maximum(mean * rng.lognormal(0.0, noise, periods), 0.1))

    order_up_to = round(base * cover_days)
    on_hand = order_up_to
    pipeline = np.zeros(periods + LEAD_DAYS + 1, dtype=int)
    available = np.zeros(periods, dtype=int)
    for index in range(periods):
        on_hand += int(pipeline[index])
        available[index] = on_hand
        on_hand = max(0, on_hand - int(min(demand[index], on_hand)))
        if index % REVIEW_DAYS == 0:
            position = on_hand + int(pipeline[index + 1 : index + LEAD_DAYS + 1].sum())
            pipeline[index + LEAD_DAYS] += max(0, order_up_to - position)

    sales, censored = censor(demand, available)
    return Series(item=item, demand=demand, available=available, sales=sales, censored=censored)


def generate_panel(
    items: int = 40, periods: int = 364, seed: int = DEFAULT_SEED, cover_days: float = 12.0
) -> list[Series]:
    """A panel of items whose bases and volatilities differ.

    Items differ so that the panel's aggregate censoring rate is a mixture
    rather than one number repeated, which is what a real assortment looks like
    and what makes the weighted figures in this repository non trivial.
    """
    rng = np.random.default_rng(seed)
    out = []
    for index in range(items):
        out.append(
            generate_item(
                item=f"SKU-{index:03d}",
                periods=periods,
                base=float(rng.uniform(12.0, 120.0)),
                seasonal_amplitude=float(rng.uniform(0.15, 0.5)),
                noise=float(rng.uniform(0.15, 0.4)),
                cover_days=cover_days,
                seed=seed + 101 * index,
            )
        )
    return out
