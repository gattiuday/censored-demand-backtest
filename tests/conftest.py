"""Fixtures shared across the suite."""

from __future__ import annotations

import pytest

from cdb.generator import generate_item, generate_panel


@pytest.fixture(scope="session")
def panel():
    """The committed fixture's panel, at the cover level the headline quotes."""
    return generate_panel(items=30, cover_days=10.0)


@pytest.fixture(scope="session")
def heavy_panel():
    """A panel with enough censoring that every censoring effect is visible."""
    return generate_panel(items=30, cover_days=5.0)


@pytest.fixture
def item():
    return generate_item("SKU-TEST")


@pytest.fixture
def uncensored_item():
    """Cover so deep that nothing is censored, where sales and demand agree."""
    return generate_item("SKU-DEEP", cover_days=40.0)
