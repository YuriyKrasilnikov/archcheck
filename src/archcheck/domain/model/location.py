"""Source code location value object."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Location:
    """Exact position in source code.

    Attributes:
        file: Path to source file
        line: Line number (1-based, must be > 0)
        column: Column number (0-based, must be >= 0)
        end_line: End line for multi-line spans
        end_column: End column for multi-line spans
    """

    file: Path
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if self.file is None:
            raise TypeError("file must not be None")
        if self.line <= 0:
            raise ValueError(f"line must be > 0, got {self.line}")
        if self.column < 0:
            raise ValueError(f"column must be >= 0, got {self.column}")
        if self.end_line is not None and self.end_line < self.line:
            raise ValueError(f"end_line ({self.end_line}) must be >= line ({self.line})")

    def __str__(self) -> str:
        """Format as file:line:column."""
        return f"{self.file}:{self.line}:{self.column}"
