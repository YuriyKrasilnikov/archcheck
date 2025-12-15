"""Function call graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from archcheck.domain.model.graph import DiGraph

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from archcheck.domain.model.module import Module


@dataclass(frozen=True, slots=True)
class CallGraph:
    """Function call relationships.

    Nodes: Function/method names (qualified or as they appear in code)
    Edges: Caller → Callee

    Note: Callee names may be simple ("print") or qualified ("self.helper")
    depending on how they appear in source code.

    Attributes:
        graph: Underlying directed graph
    """

    graph: DiGraph[str]

    def calls(self, func: str) -> frozenset[str]:
        """Get functions called by this function. O(1).

        Args:
            func: Function qualified name

        Returns:
            Set of callee names
        """
        return self.graph.successors(func)

    def called_by(self, func: str) -> frozenset[str]:
        """Get functions that call this function. O(1).

        Args:
            func: Function name

        Returns:
            Set of caller qualified names
        """
        return self.graph.predecessors(func)

    def has_call(self, caller: str, callee: str) -> bool:
        """Check if caller calls callee. O(1)."""
        return self.graph.has_edge(caller, callee)

    def has_function(self, func: str) -> bool:
        """Check if function is in graph. O(1)."""
        return self.graph.has_node(func)

    @property
    def functions(self) -> frozenset[str]:
        """All function names in graph."""
        return self.graph.nodes

    @property
    def function_count(self) -> int:
        """Number of functions."""
        return self.graph.node_count

    @property
    def call_count(self) -> int:
        """Total number of call edges."""
        return self.graph.edge_count

    @classmethod
    def from_modules(cls, modules: Mapping[str, Module]) -> CallGraph:
        """Build call graph from parsed modules.

        Args:
            modules: Module name → Module mapping

        Returns:
            CallGraph with all call relationships

        Time: O(F * C) where F=functions, C=avg calls per function

        Note:
            Uses CallInfo.target which returns resolved FQN if available,
            otherwise returns raw callee_name.
        """

        def edges() -> Iterator[tuple[str, str]]:
            for module in modules.values():
                # Module-level functions
                for func in module.functions:
                    for call_info in func.body_calls:
                        # Use resolved FQN if available, else raw name
                        yield (func.qualified_name, call_info.target)

                # Class methods
                for klass in module.classes:
                    for method in klass.methods:
                        for call_info in method.body_calls:
                            # Use resolved FQN if available, else raw name
                            yield (method.qualified_name, call_info.target)

        graph = DiGraph.from_edges(edges())
        return cls(graph=graph)

    @classmethod
    def empty(cls) -> CallGraph:
        """Create empty call graph."""
        return cls(graph=DiGraph.empty())
