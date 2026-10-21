# ADR-003: What a generated sales history cannot establish

Status: accepted

## Context

The demand column is planted. That is the only reason any figure here can be checked, and it
is also the reason a reader should know exactly which claims survive leaving this repository
and which do not. This ADR is the inventory, written so a reader does not have to work it
out from the code.

## Claims the fixture establishes

- **Sales is `min(demand, available)`.** Definitional, and asserted over every day of the
  fixture rather than assumed.
- **A sales based backtest scores a forecast against a different quantity from the one it
  predicts.** This follows from the definition and does not depend on the demand process at
  all.
- **The sales based score is the pessimistic one.** Both effects run the same way: on a
  censored day the numerator rises because the forecast is compared to a smaller number, and
  the denominator falls because the period's sales total is smaller than its demand total.
  The direction is arithmetic; the size is not.
- **No correction built from the uncensored days recovers all of the censored demand.**
  Structural, for the reason in ADR-002.

## Claims the fixture establishes only conditionally

- **The selection inversion.** That a sales based backtest prefers the uncorrected
  forecaster is general: it is being scored against the thing the uncorrected forecaster
  predicts. That the demand based backtest prefers the corrected one wherever censoring is
  material depends on the uplift being roughly right about this demand process, and it is a
  simple uplift on a lognormal Poisson demand with a weekly cycle. On a demand process with
  heavier tails the uplift would under-correct and the inversion would still be there; on one
  with a trend it could over-correct. The inversion's *existence* transfers. Its
  *size* does not.
- **The level at which the inversion disappears.** Measured at a fill rate of about 97.5% on
  this fixture. That number is a property of this demand process, this review period and
  this lead time together, and the right reading is that there is a level and a reader should
  find theirs, not that the level is the one printed here.
- **The share of the gap each correction closes, and that it falls as censoring gets
  rarer.** The direction follows from censoring selecting high demand days, which is general.
  The magnitudes are this fixture's.

## Claims this repository does not make

- **That any real operation has this problem at this size.** Nothing here measures a real
  sales history. The claim is about what a sales history can support, not about what any
  particular one contains, and `judge` is the subcommand that answers that for a real one.
- **That the uplift is the right correction.** ADR-002 names the method that probably is and
  does not implement it.
- **That `scale_by_availability` is fairly treated.** It needs an intraday stock curve and
  this fixture has daily granularity, so it is graded on a proxy that it would not be given
  in a system that had the data. It is in the table because the proxy's failure is worth
  measuring and because leaving it out would make the other two look like the only options.
  It is the one row here that is a measurement of this repository's fixture rather than of
  the method.
- **That demand is recoverable.** It is not, from a sales column. Everything in `correct.py`
  is an assumption, which is ADR-002.

## Consequences

A reader who wants to know whether this applies to them should run `judge` on their own
history, which needs no demand column, and read the censored share. The rest of this
repository is a demonstration of what that number implies, measured somewhere the answer is
known.
