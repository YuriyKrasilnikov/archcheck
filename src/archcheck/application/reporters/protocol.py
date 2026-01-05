"""Reporter protocol: contract for all reporters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from archcheck.domain.events import TrackingResult


class ReporterProtocol(Protocol):
    """Protocol for tracking result reporters.

    Output is str, not print(). Caller decides destination.
    All reporters implement same interface (No Special Cases per PHILOSOPHY).
    """

    def report(self, result: TrackingResult) -> str:
        """Format tracking result as string.

        Args:
            result: Tracking result to format.

        Returns:
            Formatted string representation.
        """
        ...
