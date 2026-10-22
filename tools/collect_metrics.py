"""Re-measure every published figure and write docs/metrics.json.

No figure here is transcribed by hand. Values come from the test suite's
machine readable reports, from the experiments' JSON, from the committed fixture
read back off disk, or from the project's own configuration. A sibling
repository hardcoded thirteen of its declared constants, which made its own
claim false and made each one a guard that could not notice the thing it was
guarding change.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "docs" / "experiments"
GENERATED_DIR = ROOT / "docs" / "generated"
METRICS_PATH = ROOT / "docs" / "metrics.json"
JUNIT_PATH = ROOT / "junit.xml"
COVERAGE_PATH = ROOT / "coverage.json"

EXPERIMENTS = (
    "exp01_selection_inversion",
    "exp02_score_gap",
    "exp03_what_the_corrections_recover",
)

#: Each metric and the phrase or phrases that must surround it in prose. The
#: forward check requires the figure to appear inside one of these; the reverse
#: check requires every number in a document to sit at an offset some anchor put
#: it at. A metric with an empty list is reported as unguarded rather than
#: silently allowed.
ANCHORS: dict[str, list[str]] = {
    "tests_total": ["{} tests"],
    "coverage_line_pct": ["{}% line coverage"],
    "headline_fill_rate_pct": [
        "at a fill rate of\n{}%",
        "every fill rate up to {}%",
        "up to as high as {}% fill",
        "fill rate of {}% and",
    ],
    "lowest_fill_rate_pct": ["rate of {}% up to"],
    "headline_unrecorded_pct": ["{}% of demand was never recorded"],
    "best_fill_where_inversion_holds_pct": ["as high as {}% fill"],
    "lowest_fill_where_selections_agree_pct": [
        "agree again at {}% fill",
        "a fill rate of about {}% on",
    ],
    "uncorrected_sales_wmape": ["Sales scores it at {}"],
    "uplifted_sales_wmape": ["against {} for the corrected one"],
    "uncorrected_demand_wmape": ["demand scores the uncorrected forecaster at {}"],
    "uplifted_demand_wmape": ["and the corrected one at {}"],
    "headline_gap_uncorrected": ["pessimistic by {} points"],
    "headline_gap_uplifted": ["and by {} points"],
    "raw_sales_share_pct": [
        "records {}% of the demand",
        "against the raw history's {}%",
    ],
    "best_correction_recovers_pct": ["puts back {}%"],
    "gap_closed_pct": ["closes {}% of the gap"],
    "gap_closed_at_lowest_cover_pct": ["closes {}% of it"],
    "fixture_items": ["{} items"],
    "fixture_days": ["{} days"],
    "python_min_version": [],
}

#: How each metric is formatted everywhere it appears. The format is part of the
#: published claim: a figure rounded to no decimals once read as a round hundred
#: when the measurement was a fifth of a point short of one, and the badge check
#: compared the badge against the same rounded value and agreed with itself.
FORMATS: dict[str, str] = {
    "tests_total": "{:d}",
    "coverage_line_pct": "{:.2f}",
    "headline_fill_rate_pct": "{:.1f}",
    "lowest_fill_rate_pct": "{:.1f}",
    "headline_unrecorded_pct": "{:.1f}",
    "best_fill_where_inversion_holds_pct": "{:.1f}",
    "lowest_fill_where_selections_agree_pct": "{:.1f}",
    "uncorrected_sales_wmape": "{:.3f}",
    "uplifted_sales_wmape": "{:.3f}",
    "uncorrected_demand_wmape": "{:.3f}",
    "uplifted_demand_wmape": "{:.3f}",
    "headline_gap_uncorrected": "{:.1f}",
    "headline_gap_uplifted": "{:.1f}",
    "raw_sales_share_pct": "{:.1f}",
    "best_correction_recovers_pct": "{:.1f}",
    "gap_closed_pct": "{:.0f}",
    "gap_closed_at_lowest_cover_pct": "{:.0f}",
    "fixture_items": "{:d}",
    "fixture_days": "{:d}",
    "python_min_version": "{}",
}

#: Which documents publish which generated blocks. The blocks are written into
#: these documents by `sync_generated_blocks` and then checked for drift, so a
#: table in prose is never a hand copy of generated output.
GENERATED_BLOCKS = {
    "README.md": ("selection-table.md", "recovery-table.md"),
}

CHECKED_DOCUMENTS = (
    "README.md",
    *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "docs" / "adr").glob("ADR-*.md")),
    *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "src" / "cdb").glob("*.py")),
    *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "experiments").glob("exp*.py")),
)


def run_tests() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-q",
            f"--junitxml={JUNIT_PATH}",
            "--cov=tta",
            "--cov-report=json",
        ],
        cwd=ROOT,
        check=True,
    )


def run_experiments() -> None:
    env_path = f"{ROOT / 'src'}:{ROOT / 'experiments'}:{ROOT / 'tests'}"
    for name in EXPERIMENTS:
        subprocess.run(
            [sys.executable, str(ROOT / "experiments" / f"{name}.py")],
            cwd=ROOT,
            check=True,
            env={"PYTHONPATH": env_path, "PATH": "/usr/bin:/bin:/usr/local/bin"},
        )


#: The one test file whose failure cannot block collection. Its tests read
#: ``docs/metrics.json`` and assert that every published figure is anchored, so
#: they are red by construction whenever the figures are stale, which is the
#: state collection exists to fix. Blocking on them deadlocks: the file cannot
#: be written until the tests pass and the tests cannot pass until it is
#: written. Every other failure still refuses, and ``make verify`` runs the full
#: suite *after* collection, so a real receipts regression still fails the
#: build. It just no longer stops the file that would clear it from being
#: written. See ADR-006.
RECEIPTS_SUITE = "tests/test_check_numbers.py"


def failing_tests(suite: ElementTree.Element) -> list[str]:
    """Names of the tests that failed or errored, as ``file::test``."""
    failures = []
    for case in suite.iter("testcase"):
        if case.find("failure") is None and case.find("error") is None:
            continue
        path = (case.get("classname") or "").split(".")
        name = case.get("name") or "?"
        failures.append(f"{'/'.join(path)}.py::{name}" if path else name)
    return failures


def read_suite() -> dict[str, float]:
    suite = ElementTree.parse(JUNIT_PATH).getroot()
    if suite.tag != "testsuite":
        suite = suite.find("testsuite")
    failures = failing_tests(suite)
    blocking = [name for name in failures if not name.startswith(RECEIPTS_SUITE)]
    if blocking:
        raise SystemExit(
            f"refusing to publish metrics from a run with {len(blocking)} failing "
            f"tests outside {RECEIPTS_SUITE}: {', '.join(sorted(blocking))}"
        )
    if failures:
        print(
            f"warning: {len(failures)} receipts tests are red, which is expected "
            "while the figures are stale. Re-run the suite after this collection "
            "and treat a remaining failure as real",
            file=sys.stderr,
        )
    coverage = json.loads(COVERAGE_PATH.read_text())
    return {
        "tests_total": int(suite.get("tests")),
        "coverage_line_pct": float(coverage["totals"]["percent_covered"]),
    }


def read_experiment(name: str) -> dict:
    return json.loads((EXPERIMENT_DIR / f"{name}.json").read_text())


TEST_COUNT_DOCUMENTS = ("README.md",)


def sync_test_count(total: int) -> None:
    """Write the measured test count into the badge and the prose that quote it.

    The count moves whenever a test is added, so every commit that added one
    also carried hand edits to keep the badge and the README sentence in step,
    and a missed edit showed up as a failing receipts check rather than as
    anything a reader would notice. A figure that has to be typed in more than
    one place is a figure that will eventually be wrong in one of them.

    The substitution is deliberately narrow: a tests badge, and the exact phrase
    "N tests" where N is some number. Anything looser would rewrite unrelated
    counts.
    """
    for document in TEST_COUNT_DOCUMENTS:
        path = ROOT / document
        body = path.read_text()
        body = re.sub(r"tests-\d+-brightgreen", f"tests-{total}-brightgreen", body)
        body = re.sub(r"\b\d+ tests\b", f"{total} tests", body)
        path.write_text(body)


def sync_generated_blocks(blocks: dict[str, str]) -> None:
    """Write each generated block into the documents that publish it.

    The blocks were pasted into the README by hand and checked for drift
    afterwards, which caught a stale table but left correcting it as a manual
    copy of generated output into prose, every time any figure moved. The paste
    is the step worth removing: a drift gate on a hand copied table tells you
    the copy is wrong, and a generated copy cannot be.

    The markers are HTML comments, so they are invisible in rendered Markdown
    and unambiguous to match, which the previous approach of matching the
    block's own text was not.
    """
    for document, names in GENERATED_BLOCKS.items():
        path = ROOT / document
        body = path.read_text()
        for name in names:
            start = f"<!-- generated: {name} -->"
            end = f"<!-- end generated: {name} -->"
            if start not in body or end not in body:
                raise SystemExit(
                    f"{document} has no markers for the generated block {name}; add "
                    f"{start} and {end} around it"
                )
            head, rest = body.split(start, 1)
            _, tail = rest.split(end, 1)
            body = f"{head}{start}\n{blocks[name]}\n{end}{tail}"
        path.write_text(body)


def derive() -> dict[str, float]:
    """Every published figure, read from a run rather than typed."""
    inversion = read_experiment("exp01_selection_inversion")
    gap = read_experiment("exp02_score_gap")
    recovery = read_experiment("exp03_what_the_corrections_recover")

    fixture = pd.read_csv(ROOT / "data" / "fixtures" / "panel.csv")
    requires = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["requires-python"]

    headline = min(inversion["series"], key=lambda row: abs(row["fill_rate_mean"] - 0.93))
    gap_headline = min(gap["series"], key=lambda row: abs(row["fill_rate_mean"] - 0.93))

    metrics = dict(read_suite())
    metrics.update(
        {
            "headline_fill_rate_pct": headline["fill_rate_mean"] * 100,
            "lowest_fill_rate_pct": min(row["fill_rate_mean"] for row in inversion["series"]) * 100,
            "headline_unrecorded_pct": gap_headline["unrecorded_demand_share_mean"] * 100,
            "best_fill_where_inversion_holds_pct": (
                inversion["best_fill_rate_where_selection_inverts"] * 100
            ),
            "lowest_fill_where_selections_agree_pct": (
                inversion["lowest_fill_rate_where_selections_agree"] * 100
            ),
            "uncorrected_sales_wmape": headline["scores"]["uncorrected"]["sales"]["mean"],
            "uplifted_sales_wmape": headline["scores"]["uplifted"]["sales"]["mean"],
            "uncorrected_demand_wmape": headline["scores"]["uncorrected"]["demand"]["mean"],
            "uplifted_demand_wmape": headline["scores"]["uplifted"]["demand"]["mean"],
            # Absolute, with the direction said in words. The measured gap is
            # negative: the sales based score is larger than the demand based
            # one. Publishing a signed figure beside the word "pessimistic"
            # would print a minus sign in a sentence that already carries the
            # sign, and a reader would reasonably read the two as disagreeing.
            "headline_gap_uncorrected": abs(gap["headline_score_gap_uncorrected"]),
            "headline_gap_uplifted": abs(gap["headline_score_gap_uplifted"]),
            "raw_sales_share_pct": recovery["headline_raw_sales_share"] * 100,
            "best_correction_recovers_pct": recovery["headline_best_recovered"] * 100,
            "gap_closed_pct": recovery["headline_gap_closed_share"] * 100,
            "gap_closed_at_lowest_cover_pct": recovery["series"][0]["gap_closed_share"] * 100,
            "fixture_items": int(fixture["item"].nunique()),
            "fixture_days": int(fixture["day"].nunique()),
            "python_min_version": float(requires.lstrip(">=~^ ")),
        }
    )
    return metrics


def render_selection_block() -> str:
    """Which forecaster each backtest selects, at every level of cover."""
    inversion = read_experiment("exp01_selection_inversion")
    header = (
        "| Fill rate | Sales backtest selects | Demand backtest selects | Agree |\n"
        "| --- | --- | --- | --- |"
    )
    rows = [
        f"| {row['fill_rate_mean']:.1%} | {row['selected_on_sales']} | "
        f"{row['selected_on_demand']} | "
        # No markdown emphasis in a generated block. `check_numbers` strips
        # emphasis from a document before reading it and compares the block
        # against the file on disk, which still has the asterisks, so a bolded
        # cell makes every figure in the table look unguarded.
        f"{'yes' if row['selected_on_sales'] == row['selected_on_demand'] else 'NO'} |"
        for row in inversion["series"]
    ]
    return "\n".join([header, *rows])


def render_recovery_block() -> str:
    """What each correction puts back, and how much of the gap that closes."""
    recovery = read_experiment("exp03_what_the_corrections_recover")
    header = (
        "| Fill rate | Raw sales | Drop censored | Uplift to clean mean | "
        "Scale by availability | Gap closed |\n| --- | --- | --- | --- | --- | --- |"
    )
    rows = []
    for row in recovery["series"]:
        values = row["recovered"]
        rows.append(
            f"| {row['fill_rate_mean']:.1%} | {row['raw_sales_share_mean']:.1%} | "
            f"{values['drop_censored']['mean']:.1%} | "
            f"{values['uplift_to_clean_mean']['mean']:.1%} | "
            f"{values['scale_by_availability']['mean']:.1%} | "
            f"{row['gap_closed_share']:.0%} |"
        )
    return "\n".join([header, *rows])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-experiments", action="store_true")
    args = parser.parse_args()

    if not args.skip_tests:
        run_tests()
    if not args.skip_experiments:
        run_experiments()

    metrics = derive()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    blocks = {
        "selection-table.md": render_selection_block(),
        "recovery-table.md": render_recovery_block(),
    }
    for name, body in blocks.items():
        (GENERATED_DIR / name).write_text(body + "\n")
    sync_generated_blocks(blocks)
    sync_test_count(int(metrics["tests_total"]))

    formatted = {name: FORMATS.get(name, "{}").format(value) for name, value in metrics.items()}
    METRICS_PATH.write_text(
        json.dumps(
            {
                "metrics": metrics,
                "formatted": formatted,
                "anchors": ANCHORS,
                "formats": FORMATS,
                "checked_documents": list(CHECKED_DOCUMENTS),
                "generated_blocks": {
                    document: list(names) for document, names in GENERATED_BLOCKS.items()
                },
                "badge_only": ["python_min_version"],
                "note": (
                    "every value here is read from a run: the test suite, the "
                    "experiments, the committed fixture, or the project's own "
                    "configuration. No figure is transcribed by hand"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"wrote {METRICS_PATH.relative_to(ROOT)} with {len(metrics)} metrics")
    for name in sorted(metrics):
        print(f"  {name:38s} {formatted[name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
