"""Coverage report for architecture analysis."""

from dataclasses import dataclass

from archcheck.domain.model.function_info import FunctionInfo


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Architecture coverage analysis report.

    Immutable value object with FAIL-FIRST validation.
    Tracks which functions were called during runtime analysis.

    Attributes:
        total: All functions in codebase
        called: Functions that were called at runtime
        uncalled: Functions that were NOT called at runtime
        dead_code: Functions identified as dead code (never reachable)
    """

    total: frozenset[FunctionInfo]
    called: frozenset[FunctionInfo]
    uncalled: frozenset[FunctionInfo]
    dead_code: frozenset[FunctionInfo]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        # called and uncalled must be disjoint
        overlap = self.called & self.uncalled
        if overlap:
            raise ValueError(f"called and uncalled overlap: {overlap}")

        # called + uncalled must equal total
        if self.called | self.uncalled != self.total:
            raise ValueError("called | uncalled must equal total")

        # dead_code must be subset of uncalled
        if not self.dead_code <= self.uncalled:
            invalid = self.dead_code - self.uncalled
            raise ValueError(f"dead_code must be subset of uncalled: {invalid}")

    @property
    def total_count(self) -> int:
        """Total number of functions."""
        return len(self.total)

    @property
    def called_count(self) -> int:
        """Number of called functions."""
        return len(self.called)

    @property
    def uncalled_count(self) -> int:
        """Number of uncalled functions."""
        return len(self.uncalled)

    @property
    def dead_code_count(self) -> int:
        """Number of dead code functions."""
        return len(self.dead_code)

    @property
    def coverage_percent(self) -> float:
        """Coverage percentage (0-100).

        Returns 100.0 if total is 0 (empty codebase = fully covered).
        """
        if self.total_count == 0:
            return 100.0
        return (self.called_count / self.total_count) * 100.0

    @classmethod
    def empty(cls) -> CoverageReport:
        """Create empty coverage report."""
        return cls(
            total=frozenset(),
            called=frozenset(),
            uncalled=frozenset(),
            dead_code=frozenset(),
        )
