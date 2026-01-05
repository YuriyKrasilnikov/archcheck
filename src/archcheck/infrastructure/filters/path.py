"""Path filters.

Filter events by file path glob patterns.
Uses fnmatch for glob matching (* matches any character including /).
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.events import Event
    from archcheck.infrastructure.filters.types import Filter


def include_paths(*patterns: str) -> Filter:
    """Create filter that includes files matching any pattern.

    Uses fnmatch: * matches any characters including /.
    For directory matching, use patterns like "*/.venv/*".

    Args:
        *patterns: Glob patterns (e.g., "*.py", "src/*").

    Returns:
        Filter that returns True for events with file matching any pattern.
        Returns False for events with None file.
    """

    def _filter(event: Event) -> bool:
        file_path = event.location.file
        if file_path is None:
            return False
        return any(fnmatch.fnmatch(file_path, p) for p in patterns)

    return _filter


def exclude_paths(*patterns: str) -> Filter:
    """Create filter that excludes files matching any pattern.

    Uses fnmatch: * matches any characters including /.
    For directory matching, use patterns like "*/.venv/*".

    Args:
        *patterns: Glob patterns to exclude (e.g., "*/.venv/*", "*test_*").

    Returns:
        Filter that returns False for events with file matching any pattern.
        Returns True for events with None file (not excluded).
    """

    def _filter(event: Event) -> bool:
        file_path = event.location.file
        if file_path is None:
            return True
        return not any(fnmatch.fnmatch(file_path, p) for p in patterns)

    return _filter
