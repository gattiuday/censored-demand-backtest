"""The command line contract: what each subcommand exits with."""

from __future__ import annotations

import pandas as pd
import pytest

from cdb.cli import main, read_panel


@pytest.fixture
def fixture_panel(tmp_path):
    out = tmp_path / "panel.csv"
    assert main(["generate", "--out", str(out), "--items", "6", "--cover-days", "8"]) == 0
    return out


def test_generate_writes_a_readable_panel(fixture_panel):
    panel = read_panel(fixture_panel)
    assert len(panel) == 6
    assert all(item.periods > 0 for item in panel)


def test_judge_exits_one_on_a_censored_history(fixture_panel, capsys):
    assert main(["judge", "--panel", str(fixture_panel)]) == 1
    assert "backtest-unsafe" in capsys.readouterr().out


def test_judge_exits_zero_on_a_history_with_almost_no_censoring(tmp_path, capsys):
    out = tmp_path / "deep.csv"
    main(["generate", "--out", str(out), "--items", "6", "--cover-days", "40"])
    assert main(["judge", "--panel", str(out)]) == 0
    assert "backtest-usable" in capsys.readouterr().out


def test_backtest_prints_both_columns_and_says_one_is_not_computable(fixture_panel, capsys):
    assert main(["backtest", "--panel", str(fixture_panel)]) == 0
    out = capsys.readouterr().out
    assert "vs demand" in out
    assert "not computable from a real sales history" in out


def test_correct_prints_the_raw_sales_share_beside_every_method(fixture_panel, capsys):
    assert main(["correct", "--panel", str(fixture_panel)]) == 0
    out = capsys.readouterr().out
    assert "(raw sales)" in out
    assert "uplift_to_clean_mean" in out


def test_a_panel_missing_a_column_exits_two(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"item": ["A"], "day": [0], "sales": [1]}).to_csv(bad, index=False)
    assert main(["judge", "--panel", str(bad)]) == 2
    assert "not a panel this tool can read" in capsys.readouterr().err


def test_a_panel_with_no_demand_at_all_exits_two(tmp_path, capsys):
    """`fill_rate` refuses, and that refusal is a malformed input rather than a finding."""
    empty = tmp_path / "zero.csv"
    pd.DataFrame(
        {
            "item": ["A"] * 3,
            "day": [0, 1, 2],
            "demand": [0, 0, 0],
            "available": [5, 5, 5],
            "sales": [0, 0, 0],
            "censored": [False, False, False],
        }
    ).to_csv(empty, index=False)
    assert main(["judge", "--panel", str(empty)]) == 2
    assert "undefined rather than perfect" in capsys.readouterr().err


def test_a_finding_exits_one_and_a_malformed_input_exits_two(tmp_path, capsys):
    """The two codes are distinct on purpose and the distinction is the class.

    `UnusableSeries` subclasses both `CensoringError` and `ValueError`, so a
    caller catching either sees it; the CLI's handler order is what resolves it
    to 2. An empty panel is the other branch: a real question this data cannot
    answer, which is 1.
    """
    empty = tmp_path / "none.csv"
    import pandas as pd

    pd.DataFrame(
        {"item": [], "day": [], "demand": [], "available": [], "sales": [], "censored": []}
    ).to_csv(empty, index=False)
    assert main(["judge", "--panel", str(empty)]) == 1
    assert "empty panel" in capsys.readouterr().err
