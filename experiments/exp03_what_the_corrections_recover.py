"""How much of the demand each correction puts back, and what it still loses.

Three assumptions about a censored day, graded against the demand that was
actually there. The grading is the only reason to believe any of them, and it is
available here only because the fixture is generated.

The expected answer, and the one worth stating before the numbers, is that none
of them recovers all of it. A censored day is censored because demand was high,
so every method that fills it from the uncensored days fills it from a sample
with the top of the distribution removed. The question is how much of the gap
each closes, not whether it closes it.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
from _harness import COVER_DAYS, ITEMS, REPLICATIONS, emit

from cdb.censor import fill_rate
from cdb.correct import CORRECTIONS, correct
from cdb.generator import DEFAULT_SEED, generate_panel


def recovered_share(panel, method: str) -> float:
    """Estimated demand over true demand, as a total across the panel.

    Totals rather than per day, because that is the quantity a planner uses the
    correction for: how much was really wanted over the period.
    """
    estimated = 0.0
    true = 0
    for item in panel:
        values, _ = correct(item, method)
        # `drop_censored` returns a shorter array, so the total it implies is
        # its mean over the full period count rather than its sum. Summing the
        # retained days directly would score it as though the dropped days had
        # no demand at all, which is a different and much worse method.
        estimated += float(values.mean()) * item.periods
        true += int(item.demand.sum())
    return estimated / true


def main() -> None:
    series, rows = [], []
    for cover in COVER_DAYS:
        per_method = {name: [] for name in CORRECTIONS}
        raw, fills = [], []
        for replication in range(REPLICATIONS):
            panel = generate_panel(
                items=ITEMS, cover_days=cover, seed=DEFAULT_SEED + 9_973 * replication
            )
            fills.append(float(np.mean([fill_rate(item) for item in panel])))
            true = sum(int(item.demand.sum()) for item in panel)
            raw.append(sum(int(item.sales.sum()) for item in panel) / true)
            for name in CORRECTIONS:
                per_method[name].append(recovered_share(panel, name))
        # What share of the missing demand the best correction puts back. The
        # recovered share alone rises with the fill rate for the trivial reason
        # that there is less to recover; this is the quantity that is not
        # trivial, and it falls as censoring gets rarer. A day is censored
        # because demand was high, and when censoring is rare only the most
        # extreme days are censored, so the mean of the uncensored days is a
        # worse estimate of them than it is when half the period is censored.
        best_here = max(CORRECTIONS, key=lambda name: float(np.mean(per_method[name])))
        raw_mean = float(np.mean(raw))
        closed = (
            (float(np.mean(per_method[best_here])) - raw_mean) / (1.0 - raw_mean)
            if raw_mean < 1.0
            else 0.0
        )
        entry = {
            "cover_days": cover,
            "fill_rate_mean": float(np.mean(fills)),
            "raw_sales_share_mean": raw_mean,
            "gap_closed_share": closed,
            "best_method": best_here,
            "recovered": {
                name: {"mean": float(np.mean(values)), "sd": float(np.std(values, ddof=1))}
                for name, values in per_method.items()
            },
        }
        series.append(entry)
        rows.append(
            (
                f"{cover:.0f}",
                f"{np.mean(fills):.1%}",
                f"{np.mean(raw):.1%}",
                *(f"{np.mean(per_method[name]):.1%}" for name in CORRECTIONS),
                f"{closed:.0%}",
            )
        )

    headline = min(series, key=lambda row: abs(row["fill_rate_mean"] - 0.93))
    best = max(CORRECTIONS, key=lambda name: headline["recovered"][name]["mean"])
    emit(
        "exp03_what_the_corrections_recover",
        {
            "question": "how much of the censored demand does each correction put back",
            "replications": REPLICATIONS,
            "items_per_panel": ITEMS,
            "series": series,
            "headline_fill_rate": headline["fill_rate_mean"],
            "headline_raw_sales_share": headline["raw_sales_share_mean"],
            "headline_best_method": best,
            "headline_best_recovered": headline["recovered"][best]["mean"],
            "headline_gap_closed_share": headline["gap_closed_share"],
            "gap_closed_falls_as_censoring_gets_rarer": bool(
                all(
                    earlier["gap_closed_share"] >= later["gap_closed_share"]
                    for earlier, later in pairwise(series)
                )
            ),
            "drop_equals_uplift_in_total": bool(
                abs(
                    headline["recovered"]["drop_censored"]["mean"]
                    - headline["recovered"]["uplift_to_clean_mean"]["mean"]
                )
                < 1e-9
            ),
            "note": (
                "dropping the censored days and filling them with the mean of the "
                "uncensored ones recover exactly the same total, because filling n days "
                "with the clean mean and then averaging over all the days is the clean "
                "mean. They are the same estimator of the total and differ only in what "
                "they hand a forecaster, which is why exp01 distinguishes them and this "
                "does not. Scaling by availability does worse than either on this "
                "fixture, which has no intraday stock curve for it to use; ADR-003 is "
                "why a method this fixture cannot supply the input for is graded anyway"
            ),
        },
        rows,
        ("cover", "fill", "raw sales", *CORRECTIONS, "gap closed"),
    )


if __name__ == "__main__":
    main()
