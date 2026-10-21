"""Console output, and the one verdict this package is willing to give.

The verdict is about the measurement rather than the forecast: whether a sales
based backtest on this history can be trusted to rank forecasters. It can, when
there is little censoring, and the output says so rather than reporting a
finding that is not there.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cdb.censor import Series, fill_rate
from cdb.errors import CensoringError

__all__ = ["BACKTEST_UNSAFE", "BACKTEST_USABLE", "Verdict", "render", "verdict"]

BACKTEST_UNSAFE = "backtest-unsafe"
BACKTEST_USABLE = "backtest-usable"

#: Share of recorded days that may be censored before a sales based backtest is
#: reported as unable to rank forecasters. Declared, not measured: it is the
#: level at which exp01 finds the selection inverting on this fixture, and a
#: different demand process would put it somewhere else.
CENSORING_LIMIT = 0.01


@dataclass(frozen=True)
class Verdict:
    """What this history can and cannot support."""

    status: str
    items: int
    censored_share: float
    fill_rate: float
    unrecorded_share: float
    reasons: list[str]

    @property
    def exit_code(self) -> int:
        return 1 if self.status == BACKTEST_UNSAFE else 0


def verdict(panel: list[Series]) -> Verdict:
    """Judge the panel's sales history as a basis for ranking forecasters."""
    if not panel:
        raise CensoringError("an empty panel has no history to judge")
    censored = float(np.mean([item.censored_share for item in panel]))
    filled = float(np.mean([fill_rate(item) for item in panel]))
    demanded = sum(int(item.demand.sum()) for item in panel)
    lost = sum(item.lost_units for item in panel)
    unrecorded = lost / demanded if demanded else 0.0

    reasons = []
    if censored > CENSORING_LIMIT:
        status = BACKTEST_UNSAFE
        reasons.append(
            f"{censored:.1%} of recorded days are censored, so the sales column on those "
            "days is a floor on demand and not a measurement of it"
        )
        reasons.append(
            f"{unrecorded:.1%} of demand was never recorded, and a backtest scored against "
            "the recorded part will prefer a forecaster that predicts the recorded part"
        )
        reasons.append(
            "ranking forecasters on this history selects for predicting your own stockouts; "
            "the ranking cannot be repaired from the sales column alone"
        )
    else:
        status = BACKTEST_USABLE
        reasons.append(
            f"{censored:.1%} of recorded days are censored, below the declared limit of "
            f"{CENSORING_LIMIT:.0%}, so a sales based backtest ranks forecasters the same "
            "way a demand based one would"
        )
    return Verdict(
        status=status,
        items=len(panel),
        censored_share=censored,
        fill_rate=filled,
        unrecorded_share=unrecorded,
        reasons=reasons,
    )


def render(result: Verdict) -> str:
    """The verdict as a console block."""
    lines = [
        f"status: {result.status}",
        f"items: {result.items}",
        f"fill rate: {result.fill_rate:.1%}",
        f"censored days: {result.censored_share:.1%}",
        f"demand never recorded: {result.unrecorded_share:.1%}",
        "",
    ]
    lines.extend(f"- {reason}" for reason in result.reasons)
    return "\n".join(lines)
