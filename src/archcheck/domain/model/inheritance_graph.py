"""Class inheritance graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from archcheck.domain.model.graph import DiGraph

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from archcheck.domain.model.module import Module


@dataclass(frozen=True, slots=True)
class InheritanceGraph:
    """Class inheritance relationships.

    Nodes: Class names (qualified or simple depending on AST)
    Edges: Child → Parent (inheritance direction)

    Note: Base class names may be simple ("ABC") or qualified ("abc.ABC")
    depending on how they appear in source code.

    Attributes:
        graph: Underlying directed graph
    """

    graph: DiGraph[str]

    def bases_of(self, cls: str) -> frozenset[str]:
        """Get direct base classes. O(1).

        Args:
            cls: Class qualified name

        Returns:
            Set of base class names
        """
        return self.graph.successors(cls)

    def subclasses_of(self, cls: str) -> frozenset[str]:
        """Get direct subclasses. O(1).

        Args:
            cls: Class name (may be qualified or simple)

        Returns:
            Set of subclass qualified names
        """
        return self.graph.predecessors(cls)

    def has_base(self, cls: str, base: str) -> bool:
        """Check if cls directly inherits from base. O(1)."""
        return self.graph.has_edge(cls, base)

    def has_class(self, cls: str) -> bool:
        """Check if class is in graph. O(1)."""
        return self.graph.has_node(cls)

    @property
    def classes(self) -> frozenset[str]:
        """All class names in graph."""
        return self.graph.nodes

    @property
    def class_count(self) -> int:
        """Number of classes."""
        return self.graph.node_count

    @property
    def inheritance_count(self) -> int:
        """Total number of inheritance edges."""
        return self.graph.edge_count

    @classmethod
    def from_modules(cls, modules: Mapping[str, Module]) -> InheritanceGraph:
        """Build inheritance graph from parsed modules.

        Args:
            modules: Module name → Module mapping

        Returns:
            InheritanceGraph with all inheritance relationships

        Time: O(C * B) where C=classes, B=avg bases per class
        """

        def edges() -> Iterator[tuple[str, str]]:
            for module in modules.values():
                for klass in module.classes:
                    for base in klass.bases:
                        yield (klass.qualified_name, base)

        graph = DiGraph.from_edges(edges())
        return cls(graph=graph)

    @classmethod
    def empty(cls) -> InheritanceGraph:
        """Create empty inheritance graph."""
        return cls(graph=DiGraph.empty())
