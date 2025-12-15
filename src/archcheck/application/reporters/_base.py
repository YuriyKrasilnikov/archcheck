"""Base reporter class for output formatting.

Provides default implementation of ReporterProtocol.
Concrete reporters inherit from this.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.check_result import CheckResult


class BaseReporter(ABC):
    """Base class for reporters implementing ReporterProtocol.

    Concrete reporters must implement the report() method.
    archcheck provides PlainTextReporter and JSONReporter as defaults.
    Users can implement RichReporter, HTMLReporter, etc.

    Example:
        class MyReporter(BaseReporter):
            def report(self, result: CheckResult) -> None:
                print(f"Violations: {result.violation_count}")
    """

    @abstractmethod
    def report(self, result: CheckResult) -> None:
        """Report check results.

        Implementation decides output format and destination.

        Args:
            result: Complete check result with violations, coverage, stats
        """
