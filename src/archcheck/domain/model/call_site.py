"""Call site value object for runtime analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.location import Location


@dataclass(frozen=True, slots=True)
class CallSite:
    """Position of function call in source code.

    Immutable value object with FAIL-FIRST validation.
    Used for runtime call graph tracking.

    Attributes:
        module: Fully qualified module name (e.g., "app.services.dashboard")
        function: Function/method name (e.g., "DashboardService.list")
        line: Line number in source (1-based, must be >= 1)
        file: Path to source file
    """

    module: str
    function: str
    line: int
    file: Path

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.module:
            raise ValueError("module must not be empty")
        if not self.function:
            raise ValueError("function must not be empty")
        if self.line < 1:
            raise ValueError(f"line must be >= 1, got {self.line}")
        if self.file is None:
            raise TypeError("file must not be None")

    @property
    def fqn(self) -> str:
        """Fully qualified name: module.function."""
        return f"{self.module}.{self.function}"

    def to_location(self) -> Location:
        """Convert to Location for Violation creation.

        Returns:
            Location with file, line, column=0
        """
        from archcheck.domain.model.location import Location

        return Location(file=self.file, line=self.line, column=0)

    def __str__(self) -> str:
        """Format as file:line (module.function)."""
        return f"{self.file}:{self.line} ({self.fqn})"
