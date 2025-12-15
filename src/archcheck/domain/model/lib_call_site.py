"""Library call site value object for runtime analysis."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LibCallSite:
    """External library function call.

    Immutable value object with FAIL-FIRST validation.
    Used for tracking app → library boundaries.

    Attributes:
        lib_name: Normalized library name (e.g., "aiohttp", "sqlalchemy")
        function: Function/method name (e.g., "ClientSession.get")
    """

    lib_name: str
    function: str

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.lib_name:
            raise ValueError("lib_name must not be empty")
        if not self.function:
            raise ValueError("function must not be empty")

    @property
    def fqn(self) -> str:
        """Fully qualified name: lib_name.function."""
        return f"{self.lib_name}.{self.function}"

    def __str__(self) -> str:
        """Format as lib_name.function."""
        return self.fqn
