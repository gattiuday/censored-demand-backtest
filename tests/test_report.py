"""The verdict, and the exit code it carries."""

from __future__ import annotations

import pytest

from cdb.errors import CensoringError
from cdb.generator import generate_panel
from cdb.report import BACKTEST_UNSAFE, BACKTEST_USABLE, render, verdict


def test_a_censored_history_is_reported_unsafe_for_ranking(panel):
    result = verdict(panel)
    assert result.status == BACKTEST_UNSAFE
    assert result.exit_code == 1
    assert any("floor on demand" in reason for reason in result.reasons)


def test_a_history_with_almost_no_censoring_is_reported_usable():
    result = verdict(generate_panel(items=10, cover_days=40.0))
    assert result.status == BACKTEST_USABLE
    assert result.exit_code == 0
    assert any("below the declared limit" in reason for reason in result.reasons)


def test_an_empty_panel_is_refused():
    with pytest.raises(CensoringError, match="empty panel"):
        verdict([])


def test_the_rendered_block_states_the_unrecorded_share(panel):
    text = render(verdict(panel))
    assert "demand never recorded" in text
    assert "status: " in text
