"""Rule validation exceptions."""

from archcheck.domain.exceptions.base import ArchCheckError


class RuleValidationError(ArchCheckError):
    """Error in rule definition.

    Raised when rule configuration is invalid.
    FAIL-FIRST: validates inputs immediately.

    Attributes:
        rule_name: Name of invalid rule (must not be empty)
        reason: Why rule is invalid (must not be empty)
    """

    def __init__(self, rule_name: str, reason: str) -> None:
        # FAIL-FIRST validation
        if not rule_name:
            raise ValueError("rule_name must not be empty")
        if not reason:
            raise ValueError("reason must not be empty")

        self.rule_name = rule_name
        self.reason = reason
        super().__init__(f"Invalid rule '{rule_name}': {reason}")
