"""Codebase aggregate root."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.call_graph import CallGraph
    from archcheck.domain.model.class_ import Class
    from archcheck.domain.model.function import Function
    from archcheck.domain.model.import_graph import ImportGraph
    from archcheck.domain.model.inheritance_graph import InheritanceGraph
    from archcheck.domain.model.module import Module


@dataclass(slots=True)
class Codebase:
    """Aggregate root for entire codebase.

    The only mutable entity in domain model.
    Owns all Module instances and cached graphs.

    Attributes:
        root_path: Root directory path
        root_package: Root package name
        modules: Module name -> Module mapping
    """

    root_path: Path
    root_package: str
    modules: dict[str, Module] = field(default_factory=dict)
    _import_graph: ImportGraph | None = field(default=None, repr=False)
    _inheritance_graph: InheritanceGraph | None = field(default=None, repr=False)
    _call_graph: CallGraph | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.root_package:
            raise ValueError("root_package must not be empty")

    def get_module(self, name: str) -> Module | None:
        """Get module by full name. Returns None if not found."""
        return self.modules.get(name)

    def get_class(self, qualified_name: str) -> Class | None:
        """Get class by qualified name (module.ClassName).

        Returns None if module or class not found.
        """
        parts = qualified_name.rsplit(".", 1)
        if len(parts) != 2:
            return None

        module_name, class_name = parts
        module = self.get_module(module_name)
        if module is None:
            return None

        for cls in module.classes:
            if cls.name == class_name:
                return cls
        return None

    def iter_modules(self) -> Sequence[Module]:
        """Iterate all modules."""
        return tuple(self.modules.values())

    def iter_classes(self) -> Iterator[Class]:
        """Iterate all classes across all modules."""
        for module in self.modules.values():
            yield from module.classes

    def iter_functions(self) -> Iterator[Function]:
        """Iterate all functions (module-level and methods)."""
        for module in self.modules.values():
            yield from module.functions
            for cls in module.classes:
                yield from cls.methods

    def add_module(self, module: Module) -> None:
        """Add module to codebase.

        Invalidates cached graphs.

        Raises:
            ValueError: If module with same name already exists
        """
        if module.name in self.modules:
            raise ValueError(f"module '{module.name}' already exists in codebase")
        self.modules[module.name] = module
        # Invalidate cached graphs
        self._import_graph = None
        self._inheritance_graph = None
        self._call_graph = None

    # =========================================================================
    # Graph accessors
    # =========================================================================

    @property
    def import_graph(self) -> ImportGraph:
        """Get import dependency graph.

        Raises:
            ValueError: If graph has not been set
        """
        if self._import_graph is None:
            raise ValueError("import_graph has not been set")
        return self._import_graph

    @property
    def inheritance_graph(self) -> InheritanceGraph:
        """Get class inheritance graph.

        Raises:
            ValueError: If graph has not been set
        """
        if self._inheritance_graph is None:
            raise ValueError("inheritance_graph has not been set")
        return self._inheritance_graph

    @property
    def call_graph(self) -> CallGraph:
        """Get function call graph.

        Raises:
            ValueError: If graph has not been set
        """
        if self._call_graph is None:
            raise ValueError("call_graph has not been set")
        return self._call_graph

    def set_import_graph(self, graph: ImportGraph) -> None:
        """Set import dependency graph."""
        self._import_graph = graph

    def set_inheritance_graph(self, graph: InheritanceGraph) -> None:
        """Set class inheritance graph."""
        self._inheritance_graph = graph

    def set_call_graph(self, graph: CallGraph) -> None:
        """Set function call graph."""
        self._call_graph = graph

    def has_import_graph(self) -> bool:
        """Check if import graph is set."""
        return self._import_graph is not None

    def has_inheritance_graph(self) -> bool:
        """Check if inheritance graph is set."""
        return self._inheritance_graph is not None

    def has_call_graph(self) -> bool:
        """Check if call graph is set."""
        return self._call_graph is not None
