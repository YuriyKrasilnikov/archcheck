"""DRY helpers for DSL Query and Assertion classes.

Internal module - not part of public API.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.violation import Violation


def execute_query[T](
    source: Iterable[T],
    filters: tuple[Callable[[T], bool], ...],
) -> tuple[T, ...]:
    """Apply filters to source items.

    Args:
        source: Iterable of items to filter
        filters: Predicates to apply (all must pass)

    Returns:
        Tuple of items matching all filters

    Complexity: O(N * F) where N=items, F=filters
    """
    result: Iterable[T] = source
    for predicate in filters:
        result = filter(predicate, result)
    return tuple(result)


def execute_checks[T](
    items: tuple[T, ...],
    checks: tuple[Callable[[T], Violation | None], ...],
) -> tuple[Violation, ...]:
    """Run checks on items and collect violations.

    Args:
        items: Items to check
        checks: Check functions (return Violation or None)

    Returns:
        Tuple of all violations from all checks

    Complexity: O(N * C) where N=items, C=checks
    """
    violations: list[Violation] = []
    for item in items:
        for check in checks:
            violation = check(item)
            if violation is not None:
                violations.append(violation)
    return tuple(violations)


def get_layer(module_name: str) -> str:
    """Extract layer name from module name.

    Layer is the first segment after root package.
    Example: myapp.domain.user -> domain

    Args:
        module_name: Full module name

    Returns:
        Layer name or empty string if no layer
    """
    parts = module_name.split(".")
    return parts[1] if len(parts) > 1 else ""
