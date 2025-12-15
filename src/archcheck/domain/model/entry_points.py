"""Entry point categorization for call graph analysis."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntryPointCategories:
    """Categorized entry points by pattern matching.

    Immutable value object grouping entry points by their role:
    - request: HTTP request handlers, API endpoints
    - startup: Application startup hooks
    - cleanup: Cleanup/shutdown hooks
    - test: Test functions
    - other: Uncategorized entry points

    Attributes:
        request: Request handler FQNs (matched by pattern)
        startup: Startup hook FQNs
        cleanup: Cleanup hook FQNs
        test: Test function FQNs
        other: Uncategorized entry point FQNs
    """

    request: frozenset[str]
    startup: frozenset[str]
    cleanup: frozenset[str]
    test: frozenset[str]
    other: frozenset[str]

    @property
    def all_entry_points(self) -> frozenset[str]:
        """All entry points combined."""
        return self.request | self.startup | self.cleanup | self.test | self.other

    @property
    def total_count(self) -> int:
        """Total number of entry points."""
        return len(self.all_entry_points)

    @classmethod
    def empty(cls) -> EntryPointCategories:
        """Create empty entry point categories."""
        return cls(
            request=frozenset(),
            startup=frozenset(),
            cleanup=frozenset(),
            test=frozenset(),
            other=frozenset(),
        )
