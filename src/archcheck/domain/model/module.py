"""Python module entity."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.class_ import Class
    from archcheck.domain.model.function import Function
    from archcheck.domain.model.import_ import Import
    from archcheck.domain.model.resolved_class import ResolvedClass


@dataclass(frozen=True, slots=True)
class Module:
    """Python module (single .py file).

    Attributes:
        name: Full module name (package.subpackage.module)
        path: File system path
        imports: Module imports
        classes: Top-level classes (raw AST data)
        functions: Top-level functions (not methods)
        constants: UPPER_CASE names
        docstring: Module docstring
        resolved_classes: Classes with resolved base information
    """

    name: str
    path: Path
    imports: tuple[Import, ...]
    classes: tuple[Class, ...]
    functions: tuple[Function, ...]
    constants: tuple[str, ...]
    docstring: str | None = None
    resolved_classes: tuple[ResolvedClass, ...] = ()

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.name:
            raise ValueError("module name must not be empty")

        for func in self.functions:
            if func.is_method:
                raise ValueError(f"module-level function '{func.name}' must have is_method=False")

    @property
    def package(self) -> str:
        """Parent package name, empty string for top-level modules."""
        parts = self.name.rsplit(".", 1)
        return parts[0] if len(parts) > 1 else ""
