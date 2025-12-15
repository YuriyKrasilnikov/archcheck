"""Import statement entity."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.location import Location


@dataclass(frozen=True, slots=True)
class Import:
    """Python import statement.

    Represents both:
    - import X              (name=None, level=0)
    - from X import Y       (name=Y, level=0)
    - from . import Y       (name=Y, level=1, module resolved to absolute)
    - from ..X import Y     (name=Y, level=2, module resolved to absolute)

    Attributes:
        module: Full module path (resolved to absolute for relative imports)
        name: Imported name (None for 'import X')
        alias: Alias (for 'as Z')
        location: Source location
        level: Relative import level (0=absolute, 1=from ., 2=from ..)
        is_type_checking: Inside TYPE_CHECKING block
        is_conditional: Inside if/try block
        is_lazy: Inside function/method body
    """

    module: str
    name: str | None
    alias: str | None
    location: Location
    level: int = 0
    is_type_checking: bool = False
    is_conditional: bool = False
    is_lazy: bool = False

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.module:
            raise ValueError("import module must not be empty")

        if self.location is None:
            raise TypeError("location must not be None")

        if self.level < 0:
            raise ValueError(f"level must be >= 0, got {self.level}")

        if self.alias is not None and self.alias == "":
            raise ValueError("alias must be non-empty string or None")

        # Boolean fields must be bool, not None
        if not isinstance(self.is_type_checking, bool):
            raise TypeError("is_type_checking must be bool")
        if not isinstance(self.is_conditional, bool):
            raise TypeError("is_conditional must be bool")
        if not isinstance(self.is_lazy, bool):
            raise TypeError("is_lazy must be bool")

    @property
    def imported_name(self) -> str:
        """Name as it appears in code after import.

        Returns alias if present, else name, else module.
        """
        if self.alias is not None:
            return self.alias
        if self.name is not None:
            return self.name
        return self.module.rsplit(".", 1)[-1]
