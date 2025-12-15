"""Tests for domain/model/rule.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.enums import RuleCategory, Severity
from archcheck.domain.model.location import Location
from archcheck.domain.model.rule import Rule, RuleResult
from archcheck.domain.model.violation import Violation


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_violation(rule_name: str = "test-rule") -> Violation:
    """Create a valid Violation."""
    return Violation(
        rule_name=rule_name,
        message="Test violation",
        location=make_location(),
        severity=Severity.ERROR,
        category=RuleCategory.IMPORT,
        subject="test-subject",
        expected="expected",
        actual="actual",
    )


class TestRuleResultCreation:
    """Tests for valid RuleResult creation."""

    def test_passed_result(self) -> None:
        result = RuleResult(
            rule_name="no-cyclic-imports",
            passed=True,
            violations=(),
            checked_count=10,
        )
        assert result.rule_name == "no-cyclic-imports"
        assert result.passed is True
        assert result.violations == ()
        assert result.checked_count == 10

    def test_failed_result(self) -> None:
        v = make_violation("no-cyclic-imports")
        result = RuleResult(
            rule_name="no-cyclic-imports",
            passed=False,
            violations=(v,),
            checked_count=10,
        )
        assert result.passed is False
        assert result.violations == (v,)

    def test_multiple_violations(self) -> None:
        v1 = make_violation("rule1")
        v2 = make_violation("rule2")
        result = RuleResult(
            rule_name="test-rule",
            passed=False,
            violations=(v1, v2),
            checked_count=5,
        )
        assert len(result.violations) == 2

    def test_zero_checked_count(self) -> None:
        result = RuleResult(
            rule_name="test-rule",
            passed=True,
            violations=(),
            checked_count=0,
        )
        assert result.checked_count == 0

    def test_is_frozen(self) -> None:
        result = RuleResult(
            rule_name="test-rule",
            passed=True,
            violations=(),
            checked_count=0,
        )
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore[misc]


class TestRuleResultFailFirst:
    """Tests for FAIL-FIRST validation in RuleResult."""

    def test_empty_rule_name_raises(self) -> None:
        with pytest.raises(ValueError, match="rule_name must not be empty"):
            RuleResult(
                rule_name="",
                passed=True,
                violations=(),
                checked_count=0,
            )

    def test_negative_checked_count_raises(self) -> None:
        with pytest.raises(ValueError, match="checked_count must be >= 0"):
            RuleResult(
                rule_name="test-rule",
                passed=True,
                violations=(),
                checked_count=-1,
            )

    def test_passed_with_violations_raises(self) -> None:
        v = make_violation()
        with pytest.raises(ValueError, match="passed=True contradicts non-empty violations"):
            RuleResult(
                rule_name="test-rule",
                passed=True,
                violations=(v,),
                checked_count=1,
            )

    def test_failed_without_violations_raises(self) -> None:
        with pytest.raises(ValueError, match="passed=False requires at least one violation"):
            RuleResult(
                rule_name="test-rule",
                passed=False,
                violations=(),
                checked_count=1,
            )


class TestRuleResultFailed:
    """Tests for RuleResult.failed property."""

    def test_failed_when_not_passed(self) -> None:
        v = make_violation()
        result = RuleResult(
            rule_name="test-rule",
            passed=False,
            violations=(v,),
            checked_count=1,
        )
        assert result.failed is True

    def test_not_failed_when_passed(self) -> None:
        result = RuleResult(
            rule_name="test-rule",
            passed=True,
            violations=(),
            checked_count=1,
        )
        assert result.failed is False


class ConcreteRule(Rule):
    """Concrete implementation of Rule for testing."""

    def __init__(
        self,
        name: str = "test-rule",
        category: RuleCategory = RuleCategory.CUSTOM,
        severity: Severity = Severity.ERROR,
        description: str = "",
    ) -> None:
        self._name = name
        self._category = category
        self._severity = severity
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> RuleCategory:
        return self._category

    @property
    def severity(self) -> Severity:
        return self._severity

    @property
    def description(self) -> str:
        return self._description

    def check(self, codebase: Codebase) -> RuleResult:
        return RuleResult(
            rule_name=self.name,
            passed=True,
            violations=(),
            checked_count=len(codebase.modules),
        )


class TestRuleABC:
    """Tests for Rule abstract base class."""

    def test_concrete_implementation(self) -> None:
        rule = ConcreteRule()
        assert rule.name == "test-rule"
        assert rule.category == RuleCategory.CUSTOM
        assert rule.severity == Severity.ERROR
        assert rule.description == ""

    def test_custom_name(self) -> None:
        rule = ConcreteRule(name="my-rule")
        assert rule.name == "my-rule"

    def test_custom_category(self) -> None:
        rule = ConcreteRule(category=RuleCategory.IMPORT)
        assert rule.category == RuleCategory.IMPORT

    def test_custom_severity(self) -> None:
        rule = ConcreteRule(severity=Severity.WARNING)
        assert rule.severity == Severity.WARNING

    def test_custom_description(self) -> None:
        rule = ConcreteRule(description="This is a test rule")
        assert rule.description == "This is a test rule"

    def test_check_method(self) -> None:
        rule = ConcreteRule()
        codebase = Codebase(root_path=Path("src"), root_package="myapp")

        result = rule.check(codebase)

        assert result.rule_name == "test-rule"
        assert result.passed is True
        assert result.checked_count == 0

    def test_default_severity_is_error(self) -> None:
        # Test that the base class provides ERROR as default
        rule = ConcreteRule()
        # Override _severity to test the base class behavior
        delattr(rule, "_severity")
        assert Rule.severity.fget(rule) == Severity.ERROR  # type: ignore[union-attr]

    def test_default_description_is_empty(self) -> None:
        rule = ConcreteRule()
        delattr(rule, "_description")
        assert Rule.description.fget(rule) == ""  # type: ignore[union-attr]
