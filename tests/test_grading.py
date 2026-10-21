"""The checks that make every figure in this repository mean anything.

Each of them grades the package against demand that was planted, which a real
sales history does not contain. They were written before any prose, because the
previous repository in this series had its prose written first and spent three
audits discovering that the figures it was built around were measuring the
generator rather than the tool.
"""

from __future__ import annotations

import numpy as np
import pytest

from cdb.backtest import score
from cdb.censor import fill_rate
from cdb.correct import CORRECTIONS, correct
from cdb.forecast import FORECASTERS, forecast
from cdb.generator import generate_panel


def test_sales_never_exceed_demand_and_are_bounded_by_availability(panel):
    """The censoring mechanism, asserted rather than assumed.

    If this fails every figure here is about something other than censoring.
    """
    for item in panel:
        assert np.all(item.sales <= item.demand)
        assert np.all(item.sales <= item.available)
        assert np.all(item.sales == np.minimum(item.demand, item.available))


def test_a_day_is_flagged_censored_exactly_when_availability_bound_the_sale(panel):
    """Not when sales equal availability.

    Those differ when demand equals availability, where nothing was actually
    turned away. Counting that day as censored inflates every rate computed from
    the flag, and the error is invisible without the demand column.
    """
    for item in panel:
        assert np.all(item.censored == (item.available < item.demand))
        coincident = (item.sales == item.available) & ~item.censored
        assert np.all(item.demand[coincident] == item.available[coincident])


def test_an_uncensored_history_scores_identically_against_both_columns(uncensored_item):
    """The control. With no censoring the two backtests must be one backtest.

    A difference here would mean the two scores differ for some reason other
    than censoring, which would make every comparison in this repository
    uninterpretable.
    """
    assert uncensored_item.censored_share == 0.0
    assert fill_rate(uncensored_item) == 1.0
    for name in FORECASTERS:
        scored = score(uncensored_item, name, forecast(uncensored_item, name))
        assert scored.against_sales == pytest.approx(scored.against_demand)
        assert scored.score_gap == pytest.approx(0.0)


def test_the_sales_based_score_is_the_pessimistic_one(heavy_panel):
    """The sign, which this repository had the wrong way round in a property name.

    Scoring against sales raises the numerator on a censored day and lowers the
    denominator over the period, so both effects push the percentage up. The
    computable score is therefore worse than the truth, not better.
    """
    for name in FORECASTERS:
        scored = [score(item, name, forecast(item, name)) for item in heavy_panel]
        assert np.mean([s.score_gap for s in scored]) < 0


def test_no_correction_recovers_all_of_the_censored_demand(heavy_panel):
    """The limit that is structural rather than a defect in these three methods.

    A day is censored because demand was high, so a method that fills it from
    the uncensored days fills it from a sample with the top of the distribution
    removed. Any method that recovered all of it on this fixture would be
    reading the answer.
    """
    true = sum(int(item.demand.sum()) for item in heavy_panel)
    for method in CORRECTIONS:
        estimated = sum(
            float(correct(item, method)[0].mean()) * item.periods for item in heavy_panel
        )
        assert estimated < true, f"{method} recovered all of the demand, which it cannot"
        assert estimated > sum(int(item.sales.sum()) for item in heavy_panel), (
            f"{method} recovered less than the raw sales, so it is not a correction"
        )


def test_dropping_and_uplifting_recover_the_same_total(heavy_panel):
    """Stated because the two are published side by side and are one estimator.

    Filling n censored days with the mean of the clean ones and then averaging
    over every day gives the clean mean, which is what dropping gives. They
    differ in what they hand a forecaster and not at all in the total, and a
    reader comparing the two columns should know that before comparing them.
    """
    for item in heavy_panel:
        dropped, _ = correct(item, "drop_censored")
        uplifted, _ = correct(item, "uplift_to_clean_mean")
        assert float(dropped.mean()) == pytest.approx(float(uplifted.mean()))


def test_nothing_outside_the_censoring_module_reads_the_demand_column():
    """The property that keeps the grading honest, enforced by reading the source.

    `backtest.score` takes a series and must use `demand` only to compute the
    counterfactual score. `forecast` and `correct` must not touch it at all: if
    they did, the corrections would be graded against an input they had already
    seen and every figure in exp03 would be circular.
    """
    import inspect

    from cdb import correct as correct_module
    from cdb import forecast as forecast_module

    for module in (forecast_module, correct_module):
        source = inspect.getsource(module)
        code = "\n".join(
            line
            for line in source.split("\n")
            if not line.strip().startswith("#") and '"""' not in line
        )
        assert ".demand" not in code, (
            f"{module.__name__} reads the demand column, so anything it is graded on is circular"
        )


def test_the_selection_inverts_wherever_there_is_censoring_to_correct():
    """exp01's finding, pinned at two levels rather than left to the experiment.

    The sales based backtest selects the uncorrected forecaster because the
    uncorrected forecaster is predicting sales. The demand based one selects the
    corrected one wherever censoring is material. A team has only the first.
    """
    for cover in (5.0, 8.0):
        items = generate_panel(items=20, cover_days=cover)
        means = {}
        for name in FORECASTERS:
            scored = [score(item, name, forecast(item, name)) for item in items]
            means[name] = (
                float(np.mean([s.against_sales for s in scored])),
                float(np.mean([s.against_demand for s in scored])),
            )
        on_sales = min(FORECASTERS, key=lambda n: means[n][0])
        on_demand = min(FORECASTERS, key=lambda n: means[n][1])
        assert on_sales == "uncorrected", f"at cover {cover} the sales backtest picked {on_sales}"
        assert on_demand == "uplifted", f"at cover {cover} the demand backtest picked {on_demand}"


def test_deep_cover_removes_the_inversion_rather_than_reversing_it():
    """The boundary, which is what stops the finding being a slogan.

    With almost no censoring there is nothing to correct and the uplift is at
    best neutral, so both backtests agree. A repository that claimed the
    correction always helps would be claiming something this fixture refutes.
    """
    items = generate_panel(items=20, cover_days=16.0)
    means = {}
    for name in FORECASTERS:
        scored = [score(item, name, forecast(item, name)) for item in items]
        means[name] = float(np.mean([s.against_demand for s in scored]))
    assert abs(means["uncorrected"] - means["uplifted"]) < 0.01
