"""Rule violation entity."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.enums import RuleCategory, Severity
    from archcheck.domain.model.location import Location


@dataclass(frozen=True, slots=True)
class Violation:
    """Architecture rule violation.

    Attributes:
        rule_name: Name of violated rule
        message: Human-readable message
        location: Source location
        severity: ERROR/WARNING/INFO
        category: Rule category
        subject: What violated (class, function, module name)
        expected: What was expected
        actual: What was found
        suggestion: Fix suggestion
    """

    rule_name: str
    message: str
    location: Location
    severity: Severity
    category: RuleCategory
    subject: str
    expected: str
    actual: str
    suggestion: str | None = None

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.rule_name:
            raise ValueError("rule_name must not be empty")
        if not self.message:
            raise ValueError("message must not be empty")
        if not self.subject:
            raise ValueError("subject must not be empty")
        if not self.expected:
            raise ValueError("expected must not be empty")
        if not self.actual:
            raise ValueError("actual must not be empty")

    def __str__(self) -> str:
        """Format violation for display."""
        lines = [
            f"[{self.severity.name}] {self.rule_name}: {self.message}",
            f"  at {self.location}",
            f"  subject: {self.subject}",
            f"  expected: {self.expected}",
            f"  actual: {self.actual}",
        ]
        if self.suggestion:
            lines.append(f"  suggestion: {self.suggestion}")
        return "\n".join(lines)
