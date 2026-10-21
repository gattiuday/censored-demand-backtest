"""How far is the score a team can compute from the score they want?

exp01 answers which forecaster a sales based backtest selects. This answers the
other half: by how much the score itself is wrong, which is the number anybody
reporting forecast accuracy to a business is quoting.

Both directions matter and they run against each other. Scoring against sales
compares the forecast to a smaller number, which inflates the absolute error on
a censored day, and it divides by a smaller denominator, which inflates the
percentage. Which dominates is a measurement, and the answer is different for
the two forecasters, which is the mechanism behind exp01's inversion.
"""

from __future__ import annotations

import numpy as np
from _harness import COVER_DAYS, ITEMS, REPLICATIONS, emit

from cdb.backtest import score
from cdb.censor import fill_rate
from cdb.forecast import FORECASTERS, forecast
from cdb.generator import DEFAULT_SEED, generate_panel


def main() -> None:
    series, rows = [], []
    for cover in COVER_DAYS:
        gaps = {name: [] for name in FORECASTERS}
        fills, lost = [], []
        for replication in range(REPLICATIONS):
            panel = generate_panel(
                items=ITEMS, cover_days=cover, seed=DEFAULT_SEED + 9_973 * replication
            )
            fills.append(float(np.mean([fill_rate(item) for item in panel])))
            lost.append(
                float(
                    sum(item.lost_units for item in panel)
                    / sum(item.demand.sum() for item in panel)
                )
            )
            for name in FORECASTERS:
                scored = [score(item, name, forecast(item, name)) for item in panel]
                gaps[name].append(float(np.mean([s.score_gap for s in scored])))
        entry = {
            "cover_days": cover,
            "fill_rate_mean": float(np.mean(fills)),
            "unrecorded_demand_share_mean": float(np.mean(lost)),
            "score_gap_points": {
                name: {
                    "mean": float(np.mean(values)),
                    "sd": float(np.std(values, ddof=1)),
                }
                for name, values in gaps.items()
            },
        }
        series.append(entry)
        rows.append(
            (
                f"{cover:.0f}",
                f"{np.mean(fills):.1%}",
                f"{np.mean(lost):.1%}",
                f"{np.mean(gaps['uncorrected']):+.1f}",
                f"{np.mean(gaps['uplifted']):+.1f}",
            )
        )

    headline = min(series, key=lambda row: abs(row["fill_rate_mean"] - 0.93))
    emit(
        "exp02_score_gap",
        {
            "question": "by how much does a sales based score differ from a demand based one",
            "replications": REPLICATIONS,
            "items_per_panel": ITEMS,
            "series": series,
            "headline_fill_rate": headline["fill_rate_mean"],
            "headline_unrecorded_share": headline["unrecorded_demand_share_mean"],
            "headline_score_gap_uncorrected": headline["score_gap_points"]["uncorrected"]["mean"],
            "headline_score_gap_uplifted": headline["score_gap_points"]["uplifted"]["mean"],
            "note": (
                "the sign is the finding, and it is the opposite of what this experiment "
                "was named for. A sales based backtest reports a larger error "
                "than the forecast makes against demand, not a smaller one, because the "
                "denominator shrinks faster than the numerator grows. So the bias does "
                "not flatter the forecast and a team reading it is not being told things "
                "are better than they are. They are being told the wrong forecaster is "
                "better, which is worse, because a pessimistic number invites no "
                "correction and a wrong ranking changes what gets shipped"
            ),
        },
        rows,
        ("cover", "fill", "unrecorded", "unc pts", "upl pts"),
    )


if __name__ == "__main__":
    main()
