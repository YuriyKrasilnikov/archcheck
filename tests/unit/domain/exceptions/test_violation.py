"""Tests for domain/exceptions/violation.py."""

from pathlib import Path

import pytest

from archcheck.domain.exceptions.base import ArchCheckError
from archcheck.domain.exceptions.violation import ArchitectureViolationError
from archcheck.domain.model.enums import RuleCategory, Severity
from archcheck.domain.model.location import Location
from archcheck.domain.model.violation import Violation


def make_violation(rule_name: str = "test-rule", message: str = "Test violation") -> Violation:
    """Create a valid Violation for tests."""
    return Violation(
        rule_name=rule_name,
        message=message,
        location=Location(file=Path("test.py"), line=1, column=0),
        severity=Severity.ERROR,
        category=RuleCategory.IMPORT,
        subject="test-subject",
        expected="expected",
        actual="actual",
    )


class TestArchitectureViolationError:
    """Tests for ArchitectureViolationError exception."""

    def test_is_archcheck_error(self) -> None:
        assert issubclass(ArchitectureViolationError, ArchCheckError)

    def test_has_violations_attribute(self) -> None:
        v = make_violation()
        err = ArchitectureViolationError((v,))
        assert err.violations == (v,)

    def test_single_violation(self) -> None:
        v = make_violation()
        err = ArchitectureViolationError((v,))
        assert len(err.violations) == 1

    def test_multiple_violations(self) -> None:
        v1 = make_violation("rule1", "First violation")
        v2 = make_violation("rule2", "Second violation")
        err = ArchitectureViolationError((v1, v2))
        assert len(err.violations) == 2

    def test_message_includes_count(self) -> None:
        v1 = make_violation()
        v2 = make_violation()
        err = ArchitectureViolationError((v1, v2))
        msg = str(err)
        assert msg.startswith("Found 2 architecture violation(s):\n")

    def test_message_includes_violation_details(self) -> None:
        v = make_violation("no-import", "Import is forbidden")
        err = ArchitectureViolationError((v,))
        msg = str(err)
        assert "no-import" in msg
        assert "Import is forbidden" in msg

    def test_can_catch_as_archcheck_error(self) -> None:
        v = make_violation()
        with pytest.raises(ArchCheckError) as exc_info:
            raise ArchitectureViolationError((v,))
        assert isinstance(exc_info.value, ArchitectureViolationError)


class TestArchitectureViolationErrorFailFirst:
    """Tests for FAIL-FIRST validation in ArchitectureViolationError."""

    def test_empty_violations_raises(self) -> None:
        with pytest.raises(
            ValueError,
            match=r"^ArchitectureViolationError requires at least one violation$",
        ):
            ArchitectureViolationError(())
