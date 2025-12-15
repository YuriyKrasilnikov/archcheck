"""Callee classification info for runtime analysis."""

from dataclasses import dataclass

from archcheck.domain.model.callee_kind import CalleeKind


@dataclass(frozen=True, slots=True)
class CalleeInfo:
    """Classification result for a callee.

    Immutable value object with FAIL-FIRST validation.
    Result of classify_callee() function.

    Attributes:
        kind: Classification type (APP, TEST, LIB, OTHER)
        module: Module name if APP or TEST (None for LIB/OTHER)
        lib_name: Library name if LIB (None for APP/TEST/OTHER)
    """

    kind: CalleeKind
    module: str | None = None
    lib_name: str | None = None

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        match self.kind:
            case CalleeKind.APP | CalleeKind.TEST:
                if self.module is None:
                    raise ValueError(f"{self.kind.name} requires module")
                if not self.module:
                    raise ValueError("module must not be empty for APP/TEST")
                if self.lib_name is not None:
                    raise ValueError(f"{self.kind.name} must not have lib_name")

            case CalleeKind.LIB:
                if self.lib_name is None:
                    raise ValueError("LIB requires lib_name")
                if not self.lib_name:
                    raise ValueError("lib_name must not be empty for LIB")
                if self.module is not None:
                    raise ValueError("LIB must not have module")

            case CalleeKind.OTHER:
                if self.module is not None:
                    raise ValueError("OTHER must not have module")
                if self.lib_name is not None:
                    raise ValueError("OTHER must not have lib_name")
