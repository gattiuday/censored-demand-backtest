"""Does a backtest run on sales select the better forecaster?

The question the repository exists to answer. Two forecasters differing only in
whether they correct for censoring, scored both against the sales history a team
actually has and against the demand only a generated fixture has. The
disagreement between the two scores is not the finding; which forecaster each
score selects is.

Replicated across independent panels at each level of cover, because a
selection that comes out one way on one panel is one draw, and this repository
is about numbers that are read as if they were facts.
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
        per_rep = {name: {"sales": [], "demand": []} for name in FORECASTERS}
        fills, agree = [], []
        for replication in range(REPLICATIONS):
            panel = generate_panel(
                items=ITEMS, cover_days=cover, seed=DEFAULT_SEED + 9_973 * replication
            )
            fills.append(float(np.mean([fill_rate(item) for item in panel])))
            picked = {}
            for name in FORECASTERS:
                scored = [score(item, name, forecast(item, name)) for item in panel]
                per_rep[name]["sales"].append(float(np.mean([s.against_sales for s in scored])))
                per_rep[name]["demand"].append(float(np.mean([s.against_demand for s in scored])))
            for basis in ("sales", "demand"):
                picked[basis] = min(FORECASTERS, key=lambda n: per_rep[n][basis][-1])
            agree.append(picked["sales"] == picked["demand"])

        best_sales = min(FORECASTERS, key=lambda n: float(np.mean(per_rep[n]["sales"])))
        best_demand = min(FORECASTERS, key=lambda n: float(np.mean(per_rep[n]["demand"])))
        entry = {
            "cover_days": cover,
            "fill_rate_mean": float(np.mean(fills)),
            "selected_on_sales": best_sales,
            "selected_on_demand": best_demand,
            "selections_agree_share": float(np.mean(agree)),
            "scores": {
                name: {
                    basis: {
                        "mean": float(np.mean(values[basis])),
                        "sd": float(np.std(values[basis], ddof=1)),
                    }
                    for basis in ("sales", "demand")
                }
                for name, values in per_rep.items()
            },
        }
        series.append(entry)
        rows.append(
            (
                f"{cover:.0f}",
                f"{np.mean(fills):.1%}",
                f"{np.mean(per_rep['uncorrected']['sales']):.3f}",
                f"{np.mean(per_rep['uplifted']['sales']):.3f}",
                f"{np.mean(per_rep['uncorrected']['demand']):.3f}",
                f"{np.mean(per_rep['uplifted']['demand']):.3f}",
                f"{best_sales} / {best_demand}",
            )
        )

    disagreeing = [row for row in series if row["selected_on_sales"] != row["selected_on_demand"]]
    emit(
        "exp01_selection_inversion",
        {
            "question": "does a backtest on sales select the same forecaster as one on demand",
            "replications": REPLICATIONS,
            "items_per_panel": ITEMS,
            "series": series,
            "levels_where_selection_inverts": len(disagreeing),
            "levels_measured": len(series),
            # The lowest fill rate at which the two backtests still agree, which
            # is the boundary a reader wants. Taking the highest answers a
            # different and useless question: the deepest cover in the sweep.
            "lowest_fill_rate_where_selections_agree": min(
                (
                    row["fill_rate_mean"]
                    for row in series
                    if row["selected_on_sales"] == row["selected_on_demand"]
                ),
                default=1.0,
            ),
            "best_fill_rate_where_selection_inverts": max(
                (row["fill_rate_mean"] for row in disagreeing), default=0.0
            ),
            "note": (
                "the sales based backtest selects the uncorrected forecaster at every "
                "level of cover, because the uncorrected forecaster is predicting sales "
                "and that is what it is being scored against. The demand based backtest "
                "selects the corrected one wherever there is censoring to correct. A team "
                "with only a sales history runs the first of these and cannot run the "
                "second, so the backtest rejects the correction precisely when the "
                "correction is needed"
            ),
        },
        rows,
        ("cover", "fill", "unc|sales", "upl|sales", "unc|dem", "upl|dem", "selects s/d"),
    )


if __name__ == "__main__":
    main()
