"""Function purity analysis result."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PurityInfo:
    """Purity analysis result for a function.

    A function is pure if it has no side effects and is deterministic.

    Attributes:
        is_pure: True if function is pure
        has_io_calls: Performs I/O (print, open, requests, etc.)
        has_random: Uses random/uuid/secrets
        has_time: Uses time.time, datetime.now, etc.
        has_env_access: Reads os.environ, os.getenv
        has_global_mutation: Modifies global variables
        has_argument_mutation: Mutates arguments
        has_external_state: Accesses external state
        violations: Human-readable violation descriptions
    """

    is_pure: bool
    has_io_calls: bool = False
    has_random: bool = False
    has_time: bool = False
    has_env_access: bool = False
    has_global_mutation: bool = False
    has_argument_mutation: bool = False
    has_external_state: bool = False
    violations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        has_any_impurity = (
            self.has_io_calls
            or self.has_random
            or self.has_time
            or self.has_env_access
            or self.has_global_mutation
            or self.has_argument_mutation
            or self.has_external_state
        )

        if self.is_pure and has_any_impurity:
            raise ValueError(
                "is_pure=True contradicts impurity flags: "
                f"io={self.has_io_calls}, random={self.has_random}, "
                f"time={self.has_time}, env={self.has_env_access}, "
                f"global={self.has_global_mutation}, arg={self.has_argument_mutation}, "
                f"external={self.has_external_state}"
            )

        if not self.is_pure and not has_any_impurity and not self.violations:
            raise ValueError("is_pure=False requires at least one impurity flag or violation")
