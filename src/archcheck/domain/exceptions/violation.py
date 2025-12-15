"""Architecture violation exception."""

from __future__ import annotations

from typing import TYPE_CHECKING

from archcheck.domain.exceptions.base import ArchCheckError

if TYPE_CHECKING:
    from archcheck.domain.model.violation import Violation


class ArchitectureViolationError(ArchCheckError):
    """Architecture rules violated.

    Raised by assert_check() when violations found.

    Attributes:
        violations: All found violations
    """

    def __init__(self, violations: tuple[Violation, ...]) -> None:
        if not violations:
            raise ValueError("ArchitectureViolationError requires at least one violation")

        self.violations = violations

        msg_parts = [f"Found {len(violations)} architecture violation(s):"]
        for v in violations:
            msg_parts.append(str(v))

        super().__init__("\n".join(msg_parts))
