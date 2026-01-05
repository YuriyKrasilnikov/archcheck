"""Composite filters: AND, OR, NOT composition."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.events import Event
    from archcheck.infrastructure.filters.types import Filter


def all_of(*filters: Filter) -> Filter:
    """Create filter that requires ALL filters to pass (AND).

    Args:
        *filters: Filters to compose.

    Returns:
        Filter that returns True only if all filters return True.
        Empty filters = always True.
    """

    def _filter(event: Event) -> bool:
        return all(f(event) for f in filters)

    return _filter


def any_of(*filters: Filter) -> Filter:
    """Create filter that requires ANY filter to pass (OR).

    Args:
        *filters: Filters to compose.

    Returns:
        Filter that returns True if any filter returns True.
        Empty filters = always False.
    """

    def _filter(event: Event) -> bool:
        return any(f(event) for f in filters)

    return _filter


def negate(flt: Filter) -> Filter:
    """Create filter that negates another filter (NOT).

    Args:
        flt: Filter to negate.

    Returns:
        Filter that returns opposite of input filter.
    """

    def _filter(event: Event) -> bool:
        return not flt(event)

    return _filter
