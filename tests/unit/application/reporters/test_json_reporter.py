"""Tests for reporters/json_reporter.py."""

import io
import json
from pathlib import Path

from archcheck.application.reporters.json_reporter import JSONReporter
from archcheck.domain.model.check_result import CheckResult
from archcheck.domain.model.check_stats import CheckStats
from archcheck.domain.model.coverage_report import CoverageReport
from archcheck.domain.model.enums import RuleCategory, Severity
from archcheck.domain.model.location import Location
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from archcheck.domain.model.violation import Violation


class TestJSONReporter:
    """Tests for JSONReporter."""

    def test_outputs_valid_json(self) -> None:
        """Output is valid JSON."""
        output = io.StringIO()
        reporter = JSONReporter(output)
        result = CheckResult.empty()

        reporter.report(result)

        # Should not raise
        data = json.loads(output.getvalue())
        assert isinstance(data, dict)

    def test_reports_passed(self) -> None:
        """Reports passed: true when no violations."""
        output = io.StringIO()
        reporter = JSONReporter(output)
        result = CheckResult.empty()

        reporter.report(result)

        data = json.loads(output.getvalue())
        assert data["passed"] is True

    def test_reports_failed(self) -> None:
        """Reports passed: false when violations exist."""
        output = io.StringIO()
        reporter = JSONReporter(output)
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

        data = json.loads(output.getvalue())
        assert data["passed"] is False

    def test_reports_summary(self) -> None:
        """Reports summary with counts."""
        output = io.StringIO()
        reporter = JSONReporter(output)
        result = CheckResult.empty()

        reporter.report(result)

        data = json.loads(output.getvalue())
        assert "summary" in data
        assert data["summary"]["violation_count"] == 0
        assert data["summary"]["error_count"] == 0
        assert data["summary"]["warning_count"] == 0
        assert data["summary"]["coverage_percent"] == 100.0

    def test_reports_violations(self) -> None:
        """Reports violation details."""
        output = io.StringIO()
        reporter = JSONReporter(output)
        violation = Violation(
            rule_name="test_rule",
            message="Test message",
            location=Location(file=Path("src/module.py"), line=42, column=5),
            severity=Severity.WARNING,
            category=RuleCategory.BOUNDARIES,
            subject="subject_value",
            expected="expected_value",
            actual="actual_value",
            suggestion="suggestion_value",
        )
        result = CheckResult(
            violations=(violation,),
            coverage=CoverageReport.empty(),
            merged_graph=MergedCallGraph.empty(),
            stats=CheckStats.empty(),
        )

        reporter.report(result)

        data = json.loads(output.getvalue())
        assert len(data["violations"]) == 1
        v = data["violations"][0]
        assert v["rule_name"] == "test_rule"
        assert v["message"] == "Test message"
        assert v["severity"] == "WARNING"
        assert v["category"] == "BOUNDARIES"
        assert v["subject"] == "subject_value"
        assert v["expected"] == "expected_value"
        assert v["actual"] == "actual_value"
        assert v["suggestion"] == "suggestion_value"
        assert v["location"]["line"] == 42
        assert v["location"]["column"] == 5

    def test_reports_coverage(self) -> None:
        """Reports coverage details."""
        output = io.StringIO()
        reporter = JSONReporter(output)
        result = CheckResult.empty()

        reporter.report(result)

        data = json.loads(output.getvalue())
        assert "coverage" in data
        assert data["coverage"]["total_count"] == 0
        assert data["coverage"]["called_count"] == 0
        assert data["coverage"]["percent"] == 100.0

    def test_reports_stats(self) -> None:
        """Reports analysis statistics."""
        output = io.StringIO()
        reporter = JSONReporter(output)
        result = CheckResult.empty()

        reporter.report(result)

        data = json.loads(output.getvalue())
        assert "stats" in data
        assert data["stats"]["modules_analyzed"] == 0
        assert data["stats"]["validators_run"] == 0

    def test_compact_output(self) -> None:
        """indent=None produces compact output."""
        output = io.StringIO()
        reporter = JSONReporter(output, indent=None)
        result = CheckResult.empty()

        reporter.report(result)

        text = output.getvalue()
        # Compact output has no indentation
        assert "\n  " not in text
