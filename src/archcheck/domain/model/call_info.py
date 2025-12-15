"""Call information from static analysis."""

from dataclasses import dataclass

from archcheck.domain.model.call_type import CallType


@dataclass(frozen=True, slots=True)
class CallInfo:
    """Information about a function call found in AST.

    Immutable value object with FAIL-FIRST validation.
    Contains both raw AST data and resolved FQN when available.

    Attributes:
        callee_name: Name as it appears in source code (e.g., "func", "self.method")
        resolved_fqn: Fully qualified name if resolved, None otherwise
        line: Line number of the call (1-based)
        call_type: Type of call (FUNCTION, METHOD, CONSTRUCTOR, DECORATOR, SUPER)
    """

    callee_name: str
    resolved_fqn: str | None
    line: int
    call_type: CallType

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.callee_name:
            raise ValueError("callee_name must not be empty")
        if self.line < 1:
            raise ValueError(f"line must be >= 1, got {self.line}")

    @property
    def is_resolved(self) -> bool:
        """Check if call target was resolved to FQN."""
        return self.resolved_fqn is not None

    @property
    def target(self) -> str:
        """Get best available target name (FQN if resolved, else raw name)."""
        return self.resolved_fqn if self.resolved_fqn is not None else self.callee_name

    def __str__(self) -> str:
        """Format as target:line (type)."""
        return f"{self.target}:{self.line} ({self.call_type.name})"
