# censored-demand-backtest

**A stockout does not add noise to your sales history. It replaces demand with your own availability, and a forecast backtested against sales is scored against a number the stockout created. On this fixture the sales based backtest prefers the forecaster that ignores censoring at every fill rate up to 92.8%, and the correction it rejects is the one that is right.**

[![CI](https://github.com/GITHUB_USERNAME/censored-demand-backtest/actions/workflows/ci.yml/badge.svg)](https://github.com/GITHUB_USERNAME/censored-demand-backtest/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![Tests](https://img.shields.io/badge/tests-95-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100.00%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## The thing a sales history cannot tell you

Demand is what customers wanted. Sales is what you had. On a day with stock these are the
same number, which is why the distinction can go unexamined for years, and on a day without
stock they are not:

    sales = min(demand, stock available that day)

The second term is not noise. It is one sided, it is correlated with high demand, and it is
produced by the policy whose performance the sales history is being used to judge. A
censored day supports exactly one statement about demand: it was at least the sales figure.
Turning that into a point estimate takes an assumption from outside the data, and the
assumption decides the answer.

So this is not a precision problem that more history fixes. More history gives you more
censored days.

## The uncomfortable numbers

Measured across twelve independent panels of 30 items, one year each, at a fill rate of
92.8%, which is where a packaged goods assortment actually runs:

- **7.2% of demand was never recorded anywhere.** Not recorded imprecisely. A customer
  wanted it, there was nothing to sell them, and no row exists.
- **The sales based backtest prefers the forecaster that ignores censoring, and the demand
  based one prefers the forecaster that corrects for it.** Sales scores it at 0.319 against
  0.326 for the corrected one; demand scores the uncorrected forecaster at 0.283 and the
  corrected one at 0.280, which reverses the order. A team has the first comparison and not
  the second.
- **That inversion holds at every level of cover where censoring is material**, from a fill
  rate of 53.3% up to as high as 92.8% fill. The two backtests agree again at 97.5% fill,
  where there is almost nothing left to correct.
- **The sales based score is pessimistic by 3.6 points** for the uncorrected forecaster and
  by 4.6 points for the corrected one. It does not flatter the forecast. That is
  worse rather than better: a number saying accuracy is poor invites no investigation of the
  measurement, and the ranking it produces is still wrong.
- **The best correction puts back 95.5% of the demand against the raw history's 92.8%**,
  which closes 37% of the gap. At the lowest cover level it closes 71% of it. The share
  falls as censoring gets rarer, because a day is censored when demand is high and rare
  censoring selects only the most extreme days.

95 tests, 100.00% line coverage, and every figure above is re-measured by CI and checked
against this document in both directions on every push.

## Claim 1: the backtest rejects the correction

<!-- generated: selection-table.md -->
| Fill rate | Sales backtest selects | Demand backtest selects | Agree |
| --- | --- | --- | --- |
| 53.3% | uncorrected | uplifted | NO |
| 63.6% | uncorrected | uplifted | NO |
| 72.0% | uncorrected | uplifted | NO |
| 84.6% | uncorrected | uplifted | NO |
| 92.8% | uncorrected | uplifted | NO |
| 97.5% | uncorrected | uncorrected | yes |
| 99.9% | uncorrected | uncorrected | yes |
<!-- end generated: selection-table.md -->

The sales column selects the uncorrected forecaster everywhere, and it is not wrong to. The
uncorrected forecaster is an average of recent sales, so it predicts sales, and it is being
scored on how well it predicts sales. The corrected forecaster is the same average with the
censored days filled in, so it predicts something closer to demand, and against sales it
looks worse for exactly the reason it is better.

**A team running this comparison sees the correction make the number worse and drops it.**
That is the finding. It is not that the backtest is noisy or that the correction is hard to
tune; it is that the measurement and the objective disagree, and the measurement is the only
one on the screen.

The agreement at the top of the table is what stops this being a slogan. With almost no
censoring there is nothing to correct, the uplift is at best neutral, and both backtests
pick the same forecaster. A repository claiming the correction always helps would be
claiming something this fixture refutes.

## Claim 2: no correction recovers the demand, and the shortfall is worst where censoring is rare

<!-- generated: recovery-table.md -->
| Fill rate | Raw sales | Drop censored | Uplift to clean mean | Scale by availability | Gap closed |
| --- | --- | --- | --- | --- | --- |
| 53.3% | 53.3% | 86.6% | 86.6% | 58.6% | 71% |
| 63.6% | 63.6% | 87.8% | 87.8% | 68.3% | 67% |
| 72.0% | 72.0% | 89.4% | 89.4% | 76.2% | 62% |
| 84.6% | 84.6% | 92.5% | 92.5% | 87.1% | 51% |
| 92.8% | 92.8% | 95.5% | 95.5% | 94.0% | 37% |
| 97.5% | 97.5% | 97.9% | 97.9% | 97.9% | 18% |
| 99.9% | 99.9% | 99.9% | 99.9% | 99.9% | 15% |
<!-- end generated: recovery-table.md -->

The raw history records 92.8% of the demand at the headline level and the best correction
puts back 95.5%, which closes 37% of the gap. The last column is the one worth reading
twice. It falls monotonically as the fill rate rises, and the reason is not a defect in the
methods.

Every correction here fills a censored day from the uncensored ones. A day is censored
because demand was high relative to stock. When half the period is censored, the censored
days are ordinary days and the uncensored mean is close to them. When two days in a hundred
are censored, those two are the most extreme days of the period and the uncensored mean is a
poor estimate of them. **So the correction is least reliable exactly where a well run
operation sits**, which is the opposite of the intuition that a small problem is a small
problem.

Dropping the censored days and filling them with the clean mean recover the same total, and
the two columns showing that are one estimator printed twice. Filling n days with the clean
mean and averaging over every day gives the clean mean, which is what dropping gives. They
differ in what they hand a forecaster, which is Claim 1, and not at all in the total. A test
asserts the equality so it cannot quietly stop being true.

## What is in the fixture

30 items over 364 days, with demand drawn first and the sales column produced from it by an
order up to policy on a weekly review with a three day lead time. The policy is deliberately
ordinary; the censoring a competent operation produces is the case worth measuring, and a
pathological policy would make every figure here larger and less interesting.

The demand column is planted, which is the only reason any figure here can be checked and
the reason [ADR-003](docs/adr/ADR-003-what-a-generated-sales-history-cannot-establish.md)
exists. Read it before quoting anything: it separates the claims that follow from the
definition of censoring, which transfer anywhere, from the ones that are properties of this
demand process.

## What this cannot measure

- **Whether your history has this problem.** Run `cdb judge` on it. That needs sales and a
  censoring flag and no demand column, and it reports the censored share and refuses to rank
  forecasters above a declared limit.
- **What the right correction is.** ADR-002 names the method that probably is, a survival
  estimator treating censored days as right censored observations, and does not implement it.
- **Substitution.** A customer who wanted the out of stock item and bought the one next to
  it generated a sale on a different row. Nothing here models that, and it means the
  unrecorded share is a floor on the demand distortion rather than all of it.
- **Intraday stock.** `scale_by_availability` wants an intraday stock curve and this fixture
  has daily granularity, so it is graded on a proxy it would not be given in a system that
  had the data. It is in the table so its failure is measured rather than assumed.

## Layout

```
src/cdb/
  censor.py      the mechanism, and the four columns kept apart
  generator.py   demand planted first, sales produced by an inventory policy
  forecast.py    two forecasters differing only in the correction
  backtest.py    WMAPE against sales and against demand
  correct.py     three assumptions about a censored day
  report.py      the verdict, and the exit code it carries
  cli.py         generate, judge, backtest, correct
experiments/     three experiments writing JSON to docs/experiments/
docs/adr/        three decision records
tools/           the metrics collector and the number checker
```

## Running it

```bash
make install
make verify        # lint, test, receipts, then the suite again
cdb judge --panel data/fixtures/panel.csv
```

`judge` exits 1 when the history cannot rank forecasters and 2 when the panel is malformed.
The distinction is declared where the exception is raised rather than recovered from the
message, so `UnusableSeries` subclasses both `CensoringError` and `ValueError` and the
handler's `except` order resolves it.

## Receipts

Every figure in this README is read from a run. `tools/collect_metrics.py` reads the test
run, the coverage report and the three experiment outputs and writes `docs/metrics.json`;
`tools/check_numbers.py` then checks the documents against it in both directions. A figure
quoted outside the sentence that claims it fails the build, and so does a number in any
checked document that no anchor phrase puts there, which is what catches a figure corrupted
into another measured figure's value. The two tables above are generated into this file and
compared by equality, since their cells cannot be guarded by phrases.

Two limits, stated because the sentence above would otherwise overstate them. A figure
written in words is invisible to a digit scanner. And `#` comments and `tests/` are outside
the checked set.

## Decision records

- [ADR-001: Keep sales and demand apart in the type system](docs/adr/ADR-001-keep-sales-and-demand-apart-in-the-type-system.md)
- [ADR-002: Report the correction as an assumption, not an estimator](docs/adr/ADR-002-report-the-correction-as-an-assumption-not-an-estimator.md)
- [ADR-003: What a generated sales history cannot establish](docs/adr/ADR-003-what-a-generated-sales-history-cannot-establish.md)
