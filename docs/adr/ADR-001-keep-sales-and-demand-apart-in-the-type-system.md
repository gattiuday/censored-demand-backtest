# ADR-001: Keep sales and demand apart in the type system

Status: accepted

## Context

A sales history has one quantity column and it is read as two things. On a day with
stock, sales is demand. On a day without, it is whatever stock there was. The confusion is
not an error anyone makes deliberately; it is the default, because the column is called
`sales` or `units` or `qty` and nothing in the data says which days are which.

Every figure in this repository is about the gap between those two readings, so the first
decision is to make the gap impossible to overlook in the code.

## Decision

`Series` carries `demand`, `available`, `sales` and `censored` as four separate arrays, and
`censor()` is the only function that produces `sales` from the first two. A function that
needs demand has to ask for it by name.

The censoring flag is `available < demand`, not `sales == available`. Those differ on a day
when demand happened to equal availability, where nothing was turned away, and counting
that day as censored inflates every rate computed from the flag. The distinction is
invisible from a sales export, which is the point: a real system can only approximate the
flag, and this repository measures what the approximation costs rather than assuming it is
free.

`demand` is read in exactly three places: the generator that plants it, `backtest.score`,
which computes the counterfactual score, and the experiments that grade. A test reads the
source of `forecast.py` and `correct.py` and fails if either mentions the column, because a
correction graded against an input it has already seen is not graded at all.

## Consequences

The package cannot be pointed at a real sales export without a demand column, and that is
correct rather than a limitation to apologise for. What a real export supports is the
`judge` subcommand, which needs only sales and the censoring flag and answers the one
question that does not require demand: whether a backtest on this history can rank
forecasters at all.

The cost is that `Series` is wider than it needs to be for most of what the package does,
and a reader may mistake `demand` for something the tool is estimating. The docstring on
`censor.py` says it is not, and `report.py` prints the counterfactual column with a line
saying it is not computable from a real history.
