"""Command line entry point.

Three subcommands and three exit codes. `judge` is the one that matters: it
reports whether a sales history can rank forecasters at all, and exits 1 when it
cannot, so a scheduled job can fail rather than publish a ranking.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from cdb.backtest import score
from cdb.censor import Series, fill_rate
from cdb.correct import CORRECTIONS, correct
from cdb.errors import CensoringError, UnusableSeries
from cdb.forecast import FORECASTERS, forecast
from cdb.generator import generate_panel
from cdb.report import render, verdict

__all__ = ["main"]

COLUMNS = ("item", "day", "demand", "available", "sales", "censored")


def write_panel(panel: list[Series], path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "item": item.item,
                "day": day,
                "demand": int(item.demand[day]),
                "available": int(item.available[day]),
                "sales": int(item.sales[day]),
                "censored": bool(item.censored[day]),
            }
            for item in panel
            for day in range(item.periods)
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def read_panel(path: Path) -> list[Series]:
    frame = pd.read_csv(path)
    missing = [column for column in COLUMNS if column not in frame.columns]
    if missing:
        raise UnusableSeries(
            f"{path} is missing column(s) {', '.join(missing)}; this is not a panel this "
            "tool can read"
        )
    out = []
    for name, group in frame.groupby("item", sort=True):
        ordered = group.sort_values("day")
        out.append(
            Series(
                item=str(name),
                demand=ordered["demand"].to_numpy(),
                available=ordered["available"].to_numpy(),
                sales=ordered["sales"].to_numpy(),
                censored=ordered["censored"].to_numpy().astype(bool),
            )
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cdb", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    make = sub.add_parser("generate", help="write a panel with the demand column")
    make.add_argument("--out", type=Path, required=True)
    make.add_argument("--items", type=int, default=30)
    make.add_argument("--cover-days", type=float, default=10.0)

    judge = sub.add_parser("judge", help="can this history rank forecasters")
    judge.add_argument("--panel", type=Path, required=True)

    run = sub.add_parser("backtest", help="score every forecaster both ways")
    run.add_argument("--panel", type=Path, required=True)

    fix = sub.add_parser("correct", help="what each correction recovers")
    fix.add_argument("--panel", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            panel = generate_panel(items=args.items, cover_days=args.cover_days)
            write_panel(panel, args.out)
            print(f"wrote {len(panel)} items to {args.out}")
            return 0

        panel = read_panel(args.panel)
        if args.command == "judge":
            result = verdict(panel)
            print(render(result))
            return result.exit_code

        if args.command == "backtest":
            print(f"{'forecaster':14s} {'vs sales':>10s} {'vs demand':>10s} {'gap pts':>9s}")
            print("-" * 46)
            for name in FORECASTERS:
                scored = [score(item, name, forecast(item, name)) for item in panel]
                print(
                    f"{name:14s} {np.mean([s.against_sales for s in scored]):10.4f} "
                    f"{np.mean([s.against_demand for s in scored]):10.4f} "
                    f"{np.mean([s.score_gap for s in scored]):+9.1f}"
                )
            print()
            print("the second column is not computable from a real sales history")
            return 0

        true = sum(int(item.demand.sum()) for item in panel)
        print(f"fill rate: {np.mean([fill_rate(item) for item in panel]):.1%}")
        print(f"{'correction':24s} {'recovers':>10s}")
        print("-" * 36)
        print(f"{'(raw sales)':24s} {sum(int(i.sales.sum()) for i in panel) / true:10.1%}")
        for method in CORRECTIONS:
            estimated = sum(float(correct(item, method)[0].mean()) * item.periods for item in panel)
            print(f"{method:24s} {estimated / true:10.1%}")
        return 0
    except UnusableSeries as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except CensoringError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - exercised by the console script
    raise SystemExit(main())
