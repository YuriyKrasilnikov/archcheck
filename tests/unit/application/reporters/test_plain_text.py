"""Tests for reporters/plain_text.py."""

import io
from pathlib import Path

from archcheck.application.reporters.plain_text import PlainTextReporter
from archcheck.domain.model.check_result import CheckResult
from archcheck.domain.model.check_stats import CheckStats
from archcheck.domain.model.coverage_report import CoverageReport
from archcheck.domain.model.enums import RuleCategory, Severity
from archcheck.domain.model.location import Location
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from archcheck.domain.model.violation import Violation


class TestPlainTextReporter:
    """Tests for PlainTextReporter."""

    def test_reports_passed_result(self) -> None:
        """Reports PASSED when no violations."""
        output = io.StringIO()
        reporter = PlainTextReporter(output)
        result = CheckResult.empty()

        reporter.report(result)

        text = output.getvalue()
        assert "PASSED" in text
        assert "Violations: 0" in text

    def test_reports_failed_result(self) -> None:
        """Reports FAILED when violations exist."""
        output = io.StringIO()
        reporter = PlainTextReporter(output)
        violation = Violation(
            rule_name="test_rule",
            message="Test violation",
            location=Location(file=Path("test.py"), line=1, column=0),
            severity=Severity.ERROR,
            category=RuleCategory.COUPLING,
            subject="test",
            expected="expected",
            actual="actual",
        )
        result = CheckResult(
            violations=(violation,),
            coverage=CoverageReport.empty(),
            merged_graph=MergedCallGraph.empty(),
            stats=CheckStats.empty(),
        )

        reporter.report(result)

        text = output.getvalue()
        assert "FAILED" in text
        assert "Violations: 1" in text
        assert "test_rule" in text
        assert "Test violation" in text

    def test_reports_coverage(self) -> None:
        """Reports coverage percentage."""
        output = io.StringIO()
        reporter = PlainTextReporter(output)
        result = CheckResult.empty()

        reporter.report(result)

        text = output.getvalue()
        assert "Coverage:" in text
        assert "100.0%" in text

    def test_reports_violation_details(self) -> None:
        """Reports violation details (subject, expected, actual)."""
        output = io.StringIO()
        reporter = PlainTextReporter(output)
        violation = Violation(
            rule_name="layer_boundary",
            message="Layer violation",
            location=Location(file=Path("test.py"), line=42, column=0),
            severity=Severity.ERROR,
            category=RuleCategory.BOUNDARIES,
            subject="myapp.domain → myapp.infra",
            expected="No cross-layer calls",
            actual="Cross-layer call",
            suggestion="Use interface instead",
        )
        result = CheckResult(
            violations=(violation,),
            coverage=CoverageReport.empty(),
            merged_graph=MergedCallGraph.empty(),
            stats=CheckStats.empty(),
        )

        reporter.report(result)

        text = output.getvalue()
        assert "Subject: myapp.domain → myapp.infra" in text
        assert "Expected: No cross-layer calls" in text
        assert "Actual: Cross-layer call" in text
        assert "Suggestion: Use interface instead" in text

    def test_default_output_is_stdout(self) -> None:
        """Default output is sys.stdout."""
        reporter = PlainTextReporter()

        # Just check it doesn't raise
        assert reporter._output is not None
