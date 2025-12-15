"""Reporter protocol for output formatting.

Users extend archcheck by implementing this Protocol.
NOT rich-specific - users can adapt to any output format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from archcheck.domain.model.check_result import CheckResult


class ReporterProtocol(Protocol):
    """Contract for reporters.

    Users implement this Protocol to customize output format.
    archcheck provides PlainTextReporter and JSONReporter as defaults.
    Users can implement RichReporter, HTMLReporter, etc.

    Example:
        class RichReporter:
            def __init__(self) -> None:
                from rich.console import Console
                self._console = Console()

            def report(self, result: CheckResult) -> None:
                from rich.table import Table
                table = Table(title="Architecture Check")
                table.add_column("Metric")
                table.add_column("Value")
                table.add_row("Coverage", f"{result.coverage.coverage_percent:.1f}%")
                table.add_row("Violations", str(result.violation_count))
                self._console.print(table)
    """

    def report(self, result: CheckResult) -> None:
        """Report check results.

        Implementation decides output format and destination.
        This is the single method to implement.

        Args:
            result: Complete check result with violations, coverage, stats
        """
        ...


# Backwards compatibility alias
ReporterPort = ReporterProtocol
