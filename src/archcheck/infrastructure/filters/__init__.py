"""Infrastructure layer: stateless filter functions.

Filters are pure functions: Filter = Callable[[Event], bool]
True = include event, False = exclude event.

Usage:
    from archcheck.infrastructure.filters import Filter, include_types, exclude_paths

    # Single filter
    flt = include_types(EventType.CALL, EventType.RETURN)
    filtered = [e for e in events if flt(e)]

    # Composed filters
    flt = all_of(include_types(EventType.CALL), exclude_paths("**/test_*"))
"""

from archcheck.infrastructure.filters.composite import all_of, any_of, negate
from archcheck.infrastructure.filters.event_type import exclude_types, include_types
from archcheck.infrastructure.filters.path import exclude_paths, include_paths
from archcheck.infrastructure.filters.types import Filter

__all__ = [
    "Filter",
    "all_of",
    "any_of",
    "exclude_paths",
    "exclude_types",
    "include_paths",
    "include_types",
    "negate",
]
