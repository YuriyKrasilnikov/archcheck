"""Plain text reporter using print().

Stdlib-only reporter for simple text output.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

from archcheck.application.reporters._base import BaseReporter

if TYPE_CHECKING:
    from archcheck.domain.model.check_result import CheckResult
    from archcheck.domain.model.violation import Violation


class PlainTextReporter(BaseReporter):
    """Plain text reporter using print().

    Stdlib-only implementation for simple text output.
    Outputs to stdout by default, can be configured for any TextIO.
    """

    def __init__(self, output: TextIO | None = None) -> None:
        """Initialize reporter.

        Args:
            output: Output stream (default: sys.stdout)
        """
        self._output = output if output is not None else sys.stdout

    def report(self, result: CheckResult) -> None:
        """Report check results as plain text.

        Args:
            result: Complete check result
        """
        self._report_header()
        self._report_summary(result)

        if result.violations:
            self._report_violations(result.violations)

        self._report_footer(result)

    def _write(self, text: str = "") -> None:
        """Write line to output."""
        print(text, file=self._output)

    def _report_header(self) -> None:
        """Print report header."""
        self._write("=" * 70)
        self._write("Architecture Check Results")
        self._write("=" * 70)

    def _report_summary(self, result: CheckResult) -> None:
        """Print summary section."""
        self._write()
        self._write("Summary:")
        self._write(f"  Coverage: {result.coverage.coverage_percent:.1f}%")
        self._write(f"  Violations: {result.violation_count}")
        self._write(f"    Errors: {result.error_count}")
        self._write(f"    Warnings: {result.warning_count}")
        self._write(f"  Status: {'PASS' if result.passed else 'FAIL'}")

    def _report_violations(self, violations: tuple[Violation, ...]) -> None:
        """Print violations section."""
        self._write()
        self._write("-" * 70)
        self._write(f"Violations ({len(violations)}):")
        self._write("-" * 70)

        for i, violation in enumerate(violations, start=1):
            self._write()
            self._write(f"{i}. [{violation.severity.name}] {violation.rule_name}")
            self._write(f"   {violation.message}")
            self._write(f"   Subject: {violation.subject}")
            self._write(f"   Expected: {violation.expected}")
            self._write(f"   Actual: {violation.actual}")
            if violation.suggestion:
                self._write(f"   Suggestion: {violation.suggestion}")

    def _report_footer(self, result: CheckResult) -> None:
        """Print report footer."""
        self._write()
        self._write("=" * 70)
        status = "PASSED" if result.passed else "FAILED"
        self._write(f"Result: {status}")
        self._write("=" * 70)
