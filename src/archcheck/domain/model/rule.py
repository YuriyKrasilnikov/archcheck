"""Rule base class and result."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.codebase import Codebase
    from archcheck.domain.model.enums import RuleCategory, Severity
    from archcheck.domain.model.violation import Violation


@dataclass(frozen=True, slots=True)
class RuleResult:
    """Result of rule check.

    Attributes:
        rule_name: Name of checked rule
        passed: True if no violations
        violations: Found violations
        checked_count: Number of elements checked
    """

    rule_name: str
    passed: bool
    violations: tuple[Violation, ...]
    checked_count: int

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.rule_name:
            raise ValueError("rule_name must not be empty")

        if self.checked_count < 0:
            raise ValueError(f"checked_count must be >= 0, got {self.checked_count}")

        if self.passed and self.violations:
            raise ValueError("passed=True contradicts non-empty violations")

        if not self.passed and not self.violations:
            raise ValueError("passed=False requires at least one violation")

    @property
    def failed(self) -> bool:
        """True if rule check failed."""
        return not self.passed


class Rule(ABC):
    """Abstract base class for architecture rules.

    Subclasses must implement:
    - name: Rule identifier
    - category: Rule category
    - check: Rule check logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Rule identifier."""
        ...

    @property
    @abstractmethod
    def category(self) -> RuleCategory:
        """Rule category."""
        ...

    @property
    def severity(self) -> Severity:
        """Default severity (ERROR)."""
        from archcheck.domain.model.enums import Severity

        return Severity.ERROR

    @property
    def description(self) -> str:
        """Rule description."""
        return ""

    @abstractmethod
    def check(self, codebase: Codebase) -> RuleResult:
        """Check rule against codebase.

        Args:
            codebase: Codebase to check

        Returns:
            RuleResult with violations if any
        """
        ...
