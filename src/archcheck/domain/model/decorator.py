"""Decorator value object."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.location import Location


@dataclass(frozen=True, slots=True)
class Decorator:
    """Python decorator applied to class/function.

    Attributes:
        name: Full decorator name (e.g., "dataclass", "pytest.fixture")
        arguments: Decorator arguments as strings (e.g., ("frozen=True",))
        location: Source location, None for builtins
    """

    name: str
    arguments: tuple[str, ...] = ()
    location: Location | None = None

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.name:
            raise ValueError("decorator name must not be empty")
