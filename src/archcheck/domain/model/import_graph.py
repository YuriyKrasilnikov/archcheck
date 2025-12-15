"""Module import dependency graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from archcheck.domain.model.graph import DiGraph

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from archcheck.domain.model.module import Module


@dataclass(frozen=True, slots=True)
class ImportGraph:
    """Module import dependencies.

    Nodes: Fully qualified module names
    Edges: A → B means module A imports from module B

    Attributes:
        graph: Underlying directed graph
    """

    graph: DiGraph[str]

    def imports_of(self, module: str) -> frozenset[str]:
        """Get modules imported by this module. O(1).

        Args:
            module: Fully qualified module name

        Returns:
            Set of imported module names
        """
        return self.graph.successors(module)

    def imported_by(self, module: str) -> frozenset[str]:
        """Get modules that import this module. O(1).

        Args:
            module: Fully qualified module name

        Returns:
            Set of module names that import this module
        """
        return self.graph.predecessors(module)

    def imports_from_package(self, module: str, package: str) -> frozenset[str]:
        """Get imports from specific package.

        Args:
            module: Module to check
            package: Package prefix to filter by

        Returns:
            Imports that start with package prefix
        """
        if not package:
            raise ValueError("package must not be empty")

        return frozenset(
            imp
            for imp in self.imports_of(module)
            if imp == package or imp.startswith(f"{package}.")
        )

    def has_import(self, from_module: str, to_module: str) -> bool:
        """Check if from_module imports to_module. O(1)."""
        return self.graph.has_edge(from_module, to_module)

    def has_module(self, module: str) -> bool:
        """Check if module is in graph. O(1)."""
        return self.graph.has_node(module)

    @property
    def modules(self) -> frozenset[str]:
        """All module names in graph."""
        return self.graph.nodes

    @property
    def module_count(self) -> int:
        """Number of modules."""
        return self.graph.node_count

    @property
    def import_count(self) -> int:
        """Total number of import edges."""
        return self.graph.edge_count

    @classmethod
    def from_modules(cls, modules: Mapping[str, Module]) -> ImportGraph:
        """Build import graph from parsed modules.

        Args:
            modules: Module name → Module mapping

        Returns:
            ImportGraph with all import dependencies

        Time: O(M * I) where M=modules, I=avg imports per module
        """

        def edges() -> Iterator[tuple[str, str]]:
            for name, module in modules.items():
                for imp in module.imports:
                    yield (name, imp.module)

        all_module_names = frozenset(modules.keys())
        graph = DiGraph.from_edges(edges(), extra_nodes=all_module_names)

        return cls(graph=graph)

    @classmethod
    def empty(cls) -> ImportGraph:
        """Create empty import graph."""
        return cls(graph=DiGraph.empty())
