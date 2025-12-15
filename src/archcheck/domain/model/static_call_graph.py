"""Static call graph from AST analysis."""

from dataclasses import dataclass

from archcheck.domain.model.static_call_edge import StaticCallEdge


@dataclass(frozen=True, slots=True)
class StaticCallGraph:
    """Call graph from static (AST) analysis.

    Immutable aggregate of static analysis results.
    Contains all call edges, functions, and decorators found in AST.

    Attributes:
        edges: All call edges found in AST
        functions: All function FQNs in codebase
        decorators: All decorator FQNs found
    """

    edges: frozenset[StaticCallEdge]
    functions: frozenset[str]
    decorators: frozenset[str]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        # All edge callers must be in functions
        callers = {edge.caller_fqn for edge in self.edges}
        unknown_callers = callers - self.functions
        if unknown_callers:
            raise ValueError(f"edge callers not in functions: {unknown_callers}")

    @property
    def edge_count(self) -> int:
        """Number of call edges."""
        return len(self.edges)

    @property
    def function_count(self) -> int:
        """Number of functions."""
        return len(self.functions)

    @property
    def decorator_count(self) -> int:
        """Number of decorators."""
        return len(self.decorators)

    def get_edges_from(self, caller_fqn: str) -> frozenset[StaticCallEdge]:
        """Get all edges from a caller.

        Args:
            caller_fqn: Caller function FQN

        Returns:
            Edges where caller matches
        """
        return frozenset(edge for edge in self.edges if edge.caller_fqn == caller_fqn)

    def get_edges_to(self, callee_fqn: str) -> frozenset[StaticCallEdge]:
        """Get all edges to a callee.

        Args:
            callee_fqn: Callee function FQN

        Returns:
            Edges where callee matches
        """
        return frozenset(edge for edge in self.edges if edge.callee_fqn == callee_fqn)

    @classmethod
    def empty(cls) -> StaticCallGraph:
        """Create empty static call graph."""
        return cls(edges=frozenset(), functions=frozenset(), decorators=frozenset())
