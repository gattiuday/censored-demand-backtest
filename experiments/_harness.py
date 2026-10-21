"""Shared plumbing: deterministic setup, JSON output, a printed table."""

from __future__ import annotations

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "experiments"

#: Items per panel and panels per measurement. Every figure in this repository
#: is a mean over independent panels, because a backtest run once on one panel
#: is one draw and this repository's whole subject is backtests that are read as
#: if they were facts.
ITEMS = 30
REPLICATIONS = 12

#: Days of cover the order up to policy holds, swept because the censoring rate
#: is a policy choice rather than a property of demand, and every finding here
#: is a function of it.
COVER_DAYS = (4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0)

#: The cover level the headline figures are quoted at. Chosen as the one whose
#: fill rate is closest to the mid nineties, which is where packaged goods
#: assortments actually run, and named here so the choice is visible rather than
#: buried in a call site.
HEADLINE_COVER = 10.0


def emit(name: str, payload: dict, rows: list[tuple] | None = None, headers=()) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / f"{name}.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if rows:
        widths = [
            max(len(str(header)), *(len(str(row[i])) for row in rows))
            for i, header in enumerate(headers)
        ]
        line = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths, strict=True))
        print(line)
        print("-" * len(line))
        for row in rows:
            print("  ".join(str(c).ljust(w) for c, w in zip(row, widths, strict=True)))
    print(f"\nwrote {target.relative_to(OUTPUT_DIR.parents[1])}")
