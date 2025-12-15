"""Tests for domain/model/violation.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.enums import RuleCategory, Severity
from archcheck.domain.model.location import Location
from archcheck.domain.model.violation import Violation


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=10, column=0)


def make_minimal_violation(**kwargs: object) -> Violation:
    """Create a minimal valid Violation."""
    defaults: dict[str, object] = {
        "rule_name": "no-forbidden-import",
        "message": "Import is forbidden",
        "location": make_location(),
        "severity": Severity.ERROR,
        "category": RuleCategory.IMPORT,
        "subject": "mymodule",
        "expected": "no import of django",
        "actual": "imports django.db",
    }
    defaults.update(kwargs)
    return Violation(**defaults)  # type: ignore[arg-type]


class TestViolationCreation:
    """Tests for valid Violation creation."""

    def test_minimal_valid(self) -> None:
        v = make_minimal_violation()
        assert v.rule_name == "no-forbidden-import"
        assert v.message == "Import is forbidden"
        assert v.location == make_location()
        assert v.severity == Severity.ERROR
        assert v.category == RuleCategory.IMPORT
        assert v.subject == "mymodule"
        assert v.expected == "no import of django"
        assert v.actual == "imports django.db"
        assert v.suggestion is None

    def test_with_suggestion(self) -> None:
        v = make_minimal_violation(suggestion="Use internal module instead")
        assert v.suggestion == "Use internal module instead"

    def test_warning_severity(self) -> None:
        v = make_minimal_violation(severity=Severity.WARNING)
        assert v.severity == Severity.WARNING

    def test_info_severity(self) -> None:
        v = make_minimal_violation(severity=Severity.INFO)
        assert v.severity == Severity.INFO

    def test_all_categories(self) -> None:
        for category in RuleCategory:
            v = make_minimal_violation(category=category)
            assert v.category == category

    def test_is_frozen(self) -> None:
        v = make_minimal_violation()
        with pytest.raises(AttributeError):
            v.rule_name = "other"  # type: ignore[misc]


class TestViolationFailFirst:
    """Tests for FAIL-FIRST validation in Violation."""

    def test_empty_rule_name_raises(self) -> None:
        with pytest.raises(ValueError, match="rule_name must not be empty"):
            make_minimal_violation(rule_name="")

    def test_empty_message_raises(self) -> None:
        with pytest.raises(ValueError, match="message must not be empty"):
            make_minimal_violation(message="")

    def test_empty_subject_raises(self) -> None:
        with pytest.raises(ValueError, match="subject must not be empty"):
            make_minimal_violation(subject="")

    def test_empty_expected_raises(self) -> None:
        with pytest.raises(ValueError, match="expected must not be empty"):
            make_minimal_violation(expected="")

    def test_empty_actual_raises(self) -> None:
        with pytest.raises(ValueError, match="actual must not be empty"):
            make_minimal_violation(actual="")


class TestViolationStr:
    """Tests for Violation.__str__ method."""

    def test_str_without_suggestion(self) -> None:
        v = make_minimal_violation()
        s = str(v)
        assert "[ERROR]" in s
        assert "no-forbidden-import" in s
        assert "Import is forbidden" in s
        assert "test.py:10:0" in s
        assert "subject: mymodule" in s
        assert "expected: no import of django" in s
        assert "actual: imports django.db" in s
        assert "suggestion:" not in s

    def test_str_with_suggestion(self) -> None:
        v = make_minimal_violation(suggestion="Use myapp.db instead")
        s = str(v)
        assert "suggestion: Use myapp.db instead" in s

    def test_str_warning_severity(self) -> None:
        v = make_minimal_violation(severity=Severity.WARNING)
        s = str(v)
        assert "[WARNING]" in s

    def test_str_info_severity(self) -> None:
        v = make_minimal_violation(severity=Severity.INFO)
        s = str(v)
        assert "[INFO]" in s
