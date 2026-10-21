# ADR-002: Report the correction as an assumption, not an estimator

Status: accepted

## Context

A censored day supports exactly one statement: demand was at least the sales figure. Turning
that inequality into a number requires something the data does not contain, and the three
methods in `correct.py` each supply something different.

Dropping the censored days assumes they were missing at random. They were not: a day is
censored because demand was high relative to stock, so dropping them removes the upper tail
and the remaining mean is biased low. Filling them with the mean of the uncensored days
assumes a censored day was an average day whose sale was cut off, which corrects the count
of days and still removes the tail. Scaling by availability assumes demand arrived at a
constant rate and stock ran out partway through the day, which needs an intraday stock
curve this fixture does not have.

The temptation is to pick one, call it the demand estimate, and report a single corrected
number. That reads as a measurement and is an assumption wearing a measurement's clothes.

## Decision

Implement all three, grade each against the planted demand, and publish what each recovers
beside the raw sales figure. The raw figure is in the table because it is the baseline a
team is actually on, and a correction that did not beat it would not be a correction.

Two of the three recover the same total, and that is stated rather than left for a reader to
notice: filling n censored days with the clean mean and averaging over every day gives the
clean mean, which is what dropping gives. They are one estimator of the total and differ
only in what they hand a forecaster. A test asserts the equality so it cannot quietly stop
being true.

## Consequences

The table has a column a reader must not add up and a row that is two rows. Both are
labelled.

What the grading shows is that none of them recovers all of the censored demand, which is
structural: every method fills a censored day from a sample with the top of the
distribution removed. More usefully, the share of the gap each closes *falls* as censoring
gets rarer. When half the period is censored, the censored days are ordinary days and the
clean mean is close to them; when two days in a hundred are censored, those two are the most
extreme days in the period and the clean mean is a poor estimate of them. So the correction
is least reliable exactly where a well run operation sits, which is the opposite of the
intuition that a small problem is a small problem.

A fourth method worth having and not implemented is a survival estimator, which treats the
censored days as right censored observations and fits the demand distribution to both kinds
of day at once. It is the statistically correct answer and it needs a distributional
assumption of its own. It is named here so a reader can see what is missing rather than
inferring that these three are the field.
