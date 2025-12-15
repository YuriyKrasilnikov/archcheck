"""Function info for coverage tracking."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FunctionInfo:
    """Function information for coverage analysis.

    Immutable value object with FAIL-FIRST validation.
    Tracks function metadata for coverage reporting.

    Attributes:
        module: Fully qualified module name
        function: Function/method name
        line: Line number (1-based)
        is_async: Whether function is async
    """

    module: str
    function: str
    line: int
    is_async: bool

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.module:
            raise ValueError("module must not be empty")
        if not self.function:
            raise ValueError("function must not be empty")
        if self.line < 1:
            raise ValueError(f"line must be >= 1, got {self.line}")

    @property
    def fqn(self) -> str:
        """Fully qualified name: module.function."""
        return f"{self.module}.{self.function}"

    def __str__(self) -> str:
        """Format as module.function:line."""
        suffix = " (async)" if self.is_async else ""
        return f"{self.fqn}:{self.line}{suffix}"
