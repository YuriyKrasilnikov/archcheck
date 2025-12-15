"""Hidden dependency types for Runtime ∖ AST analysis."""

from dataclasses import dataclass
from enum import Enum, auto


class HiddenDepType(Enum):
    """Type of hidden dependency (visible only at runtime).

    Hidden dependencies are edges in Runtime graph that are NOT in AST graph.
    They indicate dynamic dispatch or framework-managed dependencies.
    """

    DI = auto()  # Dependency Injection (container resolves at runtime)
    FRAMEWORK = auto()  # Framework callbacks (aiohttp, fastapi handlers)
    DYNAMIC = auto()  # Dynamic dispatch (getattr, __getattribute__)


@dataclass(frozen=True, slots=True)
class HiddenDep:
    """Dependency visible only at runtime.

    Immutable value object with FAIL-FIRST validation.
    Represents edge in Runtime graph that is NOT in AST graph.

    Attributes:
        caller_fqn: Fully qualified name of caller
        callee_fqn: Fully qualified name of callee
        dep_type: Classification of why this dependency is hidden
    """

    caller_fqn: str
    callee_fqn: str
    dep_type: HiddenDepType

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.caller_fqn:
            raise ValueError("caller_fqn must not be empty")
        if not self.callee_fqn:
            raise ValueError("callee_fqn must not be empty")
        if self.caller_fqn == self.callee_fqn:
            raise ValueError("caller and callee must be different")

    def __str__(self) -> str:
        """Format as caller → callee (type)."""
        return f"{self.caller_fqn} → {self.callee_fqn} ({self.dep_type.name})"
