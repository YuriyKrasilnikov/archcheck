"""Function/method entity."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.call_info import CallInfo
    from archcheck.domain.model.decorator import Decorator
    from archcheck.domain.model.enums import Visibility
    from archcheck.domain.model.location import Location
    from archcheck.domain.model.parameter import Parameter
    from archcheck.domain.model.purity import PurityInfo


@dataclass(frozen=True, slots=True)
class Function:
    """Function or method definition.

    Attributes:
        name: Function name
        qualified_name: Full path (module.Class.method)
        parameters: Function parameters
        return_annotation: Return type as string, None if untyped
        decorators: Applied decorators
        location: Source location
        visibility: PUBLIC/PROTECTED/PRIVATE
        is_async: async def
        is_generator: Contains yield
        is_method: Defined inside class
        is_classmethod: Has @classmethod
        is_staticmethod: Has @staticmethod
        is_property: Has @property
        is_abstract: Has @abstractmethod
        purity_info: Purity analysis result
        body_calls: Function calls in body (with line, type, resolution info)
        body_attributes: Attributes accessed in body
        body_globals_read: Global variables read
        body_globals_write: Global variables written
    """

    name: str
    qualified_name: str
    parameters: tuple[Parameter, ...]
    return_annotation: str | None
    decorators: tuple[Decorator, ...]
    location: Location
    visibility: Visibility
    is_async: bool = False
    is_generator: bool = False
    is_method: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_property: bool = False
    is_abstract: bool = False
    purity_info: PurityInfo | None = None
    body_calls: tuple[CallInfo, ...] = ()
    body_attributes: frozenset[str] = field(default_factory=frozenset)
    body_globals_read: frozenset[str] = field(default_factory=frozenset)
    body_globals_write: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.name:
            raise ValueError("function name must not be empty")

        if not self.qualified_name:
            raise ValueError("qualified_name must not be empty")

        if self.name not in self.qualified_name:
            raise ValueError(
                f"qualified_name '{self.qualified_name}' must contain name '{self.name}'"
            )

        if self.is_classmethod and self.is_staticmethod:
            raise ValueError("function cannot be both classmethod and staticmethod")

        if self.is_property and self.is_staticmethod:
            raise ValueError("property cannot be staticmethod")

        if self.is_classmethod and not self.is_method:
            raise ValueError("classmethod must have is_method=True")

        if self.is_staticmethod and not self.is_method:
            raise ValueError("staticmethod must have is_method=True")

        if self.is_property and not self.is_method:
            raise ValueError("property must have is_method=True")
