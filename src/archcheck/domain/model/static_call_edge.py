"""Static call edge from AST analysis."""

from dataclasses import dataclass

from archcheck.domain.model.call_type import CallType


@dataclass(frozen=True, slots=True)
class StaticCallEdge:
    """Call edge from static (AST) analysis.

    Immutable value object with FAIL-FIRST validation.
    Represents a function call found by analyzing AST.

    Attributes:
        caller_fqn: Fully qualified name of calling function
        callee_fqn: Fully qualified name of called function
        line: Line number of call (1-based)
        call_type: Type of call (FUNCTION, METHOD, DECORATOR, CONSTRUCTOR, SUPER)
    """

    caller_fqn: str
    callee_fqn: str
    line: int
    call_type: CallType

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.caller_fqn:
            raise ValueError("caller_fqn must not be empty")
        if not self.callee_fqn:
            raise ValueError("callee_fqn must not be empty")
        if self.line < 1:
            raise ValueError(f"line must be >= 1, got {self.line}")

    def __str__(self) -> str:
        """Format as caller → callee:line (type)."""
        return f"{self.caller_fqn} → {self.callee_fqn}:{self.line} ({self.call_type.name})"
