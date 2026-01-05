"""Event type filters.

Filter events by EventType whitelist or blacklist.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from archcheck.domain.events import Event, EventType, get_event_type

if TYPE_CHECKING:
    from archcheck.infrastructure.filters.types import Filter


def include_types(*types: EventType) -> Filter:
    """Create filter that includes only specified event types.

    Args:
        *types: Event types to include.

    Returns:
        Filter that returns True for events matching any specified type.
    """
    type_set = frozenset(types)

    def _filter(event: Event) -> bool:
        return get_event_type(event) in type_set

    return _filter


def exclude_types(*types: EventType) -> Filter:
    """Create filter that excludes specified event types.

    Args:
        *types: Event types to exclude.

    Returns:
        Filter that returns True for events NOT matching any specified type.
    """
    type_set = frozenset(types)

    def _filter(event: Event) -> bool:
        return get_event_type(event) not in type_set

    return _filter
