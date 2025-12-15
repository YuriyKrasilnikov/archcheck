"""Class entity."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.decorator import Decorator
    from archcheck.domain.model.di import DIInfo
    from archcheck.domain.model.enums import Visibility
    from archcheck.domain.model.function import Function
    from archcheck.domain.model.location import Location


@dataclass(frozen=True, slots=True)
class Class:
    """Python class definition.

    Attributes:
        name: Class name
        qualified_name: Full path (module.Class)
        bases: Base class names
        decorators: Applied decorators
        methods: Class methods
        attributes: Class attribute names
        location: Source location
        visibility: PUBLIC/PROTECTED/PRIVATE
        is_abstract: Has abstract methods or inherits ABC
        is_dataclass: Has @dataclass decorator
        is_protocol: Inherits from Protocol
        is_exception: Inherits from Exception/BaseException
        docstring: Class docstring
        di_info: Dependency injection analysis
    """

    name: str
    qualified_name: str
    bases: tuple[str, ...]
    decorators: tuple[Decorator, ...]
    methods: tuple[Function, ...]
    attributes: tuple[str, ...]
    location: Location
    visibility: Visibility
    is_abstract: bool = False
    is_dataclass: bool = False
    is_protocol: bool = False
    is_exception: bool = False
    docstring: str | None = None
    di_info: DIInfo | None = None

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.name:
            raise ValueError("class name must not be empty")

        if not self.qualified_name:
            raise ValueError("qualified_name must not be empty")

        if self.name not in self.qualified_name:
            raise ValueError(
                f"qualified_name '{self.qualified_name}' must contain name '{self.name}'"
            )

        for method in self.methods:
            if not method.is_method:
                raise ValueError(f"method '{method.name}' must have is_method=True")
