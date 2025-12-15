"""Static call graph builder from Codebase."""

from __future__ import annotations

from typing import TYPE_CHECKING

from archcheck.domain.model.static_call_edge import StaticCallEdge
from archcheck.domain.model.static_call_graph import StaticCallGraph

if TYPE_CHECKING:
    from archcheck.domain.model.codebase import Codebase
    from archcheck.domain.model.function import Function


class StaticCallGraphBuilder:
    """Builds StaticCallGraph from Codebase.

    Extracts all function calls from AST analysis results and creates
    a StaticCallGraph with edges containing line numbers and call types.

    Stateless - no state between build() calls.
    """

    def build(self, codebase: Codebase) -> StaticCallGraph:
        """Build StaticCallGraph from codebase.

        Args:
            codebase: Parsed codebase with modules

        Returns:
            StaticCallGraph with all edges, functions, and decorators

        Raises:
            TypeError: If codebase is None (FAIL-FIRST)
        """
        if codebase is None:
            raise TypeError("codebase must not be None")

        edges: set[StaticCallEdge] = set()
        functions: set[str] = set()
        decorators: set[str] = set()

        for module in codebase.modules.values():
            # Process module-level functions
            for func in module.functions:
                self._process_function(func, edges, functions, decorators)

            # Process class methods
            for cls in module.classes:
                for method in cls.methods:
                    self._process_function(method, edges, functions, decorators)

        return StaticCallGraph(
            edges=frozenset(edges),
            functions=frozenset(functions),
            decorators=frozenset(decorators),
        )

    def _process_function(
        self,
        func: Function,
        edges: set[StaticCallEdge],
        functions: set[str],
        decorators: set[str],
    ) -> None:
        """Process single function extracting edges and metadata.

        Args:
            func: Function to process
            edges: Set to add edges to
            functions: Set to add function FQNs to
            decorators: Set to add decorator FQNs to
        """
        # Add function to set
        functions.add(func.qualified_name)

        # Add decorators
        for decorator in func.decorators:
            decorators.add(decorator.name)

        # Process calls in body
        for call_info in func.body_calls:
            # Only add edges for resolved calls
            if call_info.is_resolved and call_info.resolved_fqn is not None:
                edge = StaticCallEdge(
                    caller_fqn=func.qualified_name,
                    callee_fqn=call_info.resolved_fqn,
                    line=call_info.line,
                    call_type=call_info.call_type,
                )
                edges.add(edge)
