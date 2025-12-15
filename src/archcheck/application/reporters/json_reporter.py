"""JSON reporter for machine-readable output.

Stdlib-only reporter for JSON output.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, TextIO

from archcheck.application.reporters._base import BaseReporter

if TYPE_CHECKING:
    from archcheck.domain.model.check_result import CheckResult
    from archcheck.domain.model.violation import Violation


class JSONReporter(BaseReporter):
    """JSON reporter for machine-readable output.

    Outputs check results as JSON for CI/CD integration,
    parsing by other tools, or structured logging.
    """

    def __init__(
        self,
        output: TextIO | None = None,
        *,
        indent: int | None = 2,
    ) -> None:
        """Initialize reporter.

        Args:
            output: Output stream (default: sys.stdout)
            indent: JSON indentation (default: 2, None for compact)
        """
        self._output = output if output is not None else sys.stdout
        self._indent = indent

    def report(self, result: CheckResult) -> None:
        """Report check results as JSON.

        Args:
            result: Complete check result
        """
        data = self._result_to_dict(result)
        json.dump(data, self._output, indent=self._indent)
        self._output.write("\n")

    def _result_to_dict(self, result: CheckResult) -> dict[str, object]:
        """Convert CheckResult to JSON-serializable dict.

        Args:
            result: Check result to convert

        Returns:
            Dictionary suitable for json.dump()
        """
        return {
            "passed": result.passed,
            "summary": {
                "violation_count": result.violation_count,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "coverage_percent": result.coverage.coverage_percent,
            },
            "violations": [self._violation_to_dict(v) for v in result.violations],
            "coverage": {
                "total_count": result.coverage.total_count,
                "called_count": result.coverage.called_count,
                "uncalled_count": result.coverage.uncalled_count,
                "dead_code_count": result.coverage.dead_code_count,
                "percent": result.coverage.coverage_percent,
            },
            "stats": {
                "modules_analyzed": result.stats.modules_analyzed,
                "functions_analyzed": result.stats.functions_analyzed,
                "classes_analyzed": result.stats.classes_analyzed,
                "edges_analyzed": result.stats.edges_analyzed,
                "validators_run": result.stats.validators_run,
                "visitors_run": result.stats.visitors_run,
                "analysis_time_ms": result.stats.analysis_time_ms,
            },
        }

    def _violation_to_dict(self, violation: Violation) -> dict[str, object]:
        """Convert Violation to JSON-serializable dict.

        Args:
            violation: Violation to convert

        Returns:
            Dictionary suitable for json.dump()
        """
        return {
            "rule_name": violation.rule_name,
            "message": violation.message,
            "severity": violation.severity.name,
            "category": violation.category.name,
            "subject": violation.subject,
            "expected": violation.expected,
            "actual": violation.actual,
            "suggestion": violation.suggestion,
            "location": {
                "file": str(violation.location.file),
                "line": violation.location.line,
                "column": violation.location.column,
            },
        }
