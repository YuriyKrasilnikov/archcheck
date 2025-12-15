"""Dependency injection analysis result."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DIInfo:
    """Dependency injection analysis result for a class.

    Attributes:
        has_constructor_injection: Dependencies injected via __init__
        injected_dependencies: Type names of injected dependencies
        uses_inject_decorator: Has @inject or similar decorator
        container_registrations: Container registration points
    """

    has_constructor_injection: bool = False
    injected_dependencies: tuple[str, ...] = ()
    uses_inject_decorator: bool = False
    container_registrations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if self.injected_dependencies and not self.has_constructor_injection:
            raise ValueError("injected_dependencies requires has_constructor_injection=True")
