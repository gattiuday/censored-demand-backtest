"""Exceptions, with the exit code each one means carried by the class.

A caller wiring this into a reporting job needs to tell "the data cannot support
this question" from "the data is malformed", because the first is a finding and
the second is a bug upstream. The CLI maps the first to 1 and the second to 2,
and the mapping is read off the class rather than off the message.
"""

from __future__ import annotations

__all__ = ["CensoringError", "UnusableSeries"]


class CensoringError(Exception):
    """A question this data cannot answer. Exit code 1."""


class UnusableSeries(CensoringError, ValueError):
    """A series that is malformed rather than merely uninformative. Exit code 2.

    Subclasses both so that a caller catching `ValueError` around parsing still
    sees it, and a caller catching `CensoringError` for reporting also does.
    """
