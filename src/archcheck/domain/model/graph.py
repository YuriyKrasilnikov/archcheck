"""Immutable directed graph with O(1) bidirectional lookups.

Includes cycle detection using stdlib graphlib.TopologicalSorter.
"""

from __future__ import annotations

from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class DiGraph[T]:
    """Immutable directed graph.

    Invariants (FAIL-FIRST):
    - forward[a] contains b ⟺ reverse[b] contains a
    - All nodes in edges must be in nodes set

    Attributes:
        forward: Node → set of successors (outgoing edges)
        reverse: Node → set of predecessors (incoming edges)
        nodes: All nodes in graph (including isolated)
    """

    forward: Mapping[T, frozenset[T]]
    reverse: Mapping[T, frozenset[T]]
    nodes: frozenset[T]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        # All forward keys must be in nodes
        for node in self.forward:
            if node not in self.nodes:
                raise ValueError(f"forward key '{node}' not in nodes")

        # All successors must be in nodes
        for node, successors in self.forward.items():
            for succ in successors:
                if succ not in self.nodes:
                    raise ValueError(f"successor '{succ}' of '{node}' not in nodes")

        # All reverse keys must be in nodes
        for node in self.reverse:
            if node not in self.nodes:
                raise ValueError(f"reverse key '{node}' not in nodes")

        # All predecessors must be in nodes
        for node, predecessors in self.reverse.items():
            for pred in predecessors:
                if pred not in self.nodes:
                    raise ValueError(f"predecessor '{pred}' of '{node}' not in nodes")

        # Consistency: forward[a] contains b ⟺ reverse[b] contains a
        for node, successors in self.forward.items():
            for succ in successors:
                if node not in self.reverse.get(succ, frozenset()):
                    raise ValueError(
                        f"inconsistent: {node}→{succ} in forward but {node} not in reverse[{succ}]"
                    )

        for node, predecessors in self.reverse.items():
            for pred in predecessors:
                if node not in self.forward.get(pred, frozenset()):
                    raise ValueError(
                        f"inconsistent: {pred}→{node} in reverse but {node} not in forward[{pred}]"
                    )

    def successors(self, node: T) -> frozenset[T]:
        """Get direct successors (outgoing edges). O(1)."""
        return self.forward.get(node, frozenset())

    def predecessors(self, node: T) -> frozenset[T]:
        """Get direct predecessors (incoming edges). O(1)."""
        return self.reverse.get(node, frozenset())

    def has_edge(self, from_: T, to: T) -> bool:
        """Check if edge exists. O(1)."""
        return to in self.forward.get(from_, frozenset())

    def has_node(self, node: T) -> bool:
        """Check if node exists. O(1)."""
        return node in self.nodes

    def out_degree(self, node: T) -> int:
        """Get number of outgoing edges."""
        return len(self.successors(node))

    def in_degree(self, node: T) -> int:
        """Get number of incoming edges."""
        return len(self.predecessors(node))

    @property
    def edge_count(self) -> int:
        """Get total number of edges."""
        return sum(len(succs) for succs in self.forward.values())

    @property
    def node_count(self) -> int:
        """Get total number of nodes."""
        return len(self.nodes)

    @classmethod
    def from_edges(
        cls,
        edges: Iterable[tuple[T, T]],
        extra_nodes: frozenset[T] | None = None,
    ) -> DiGraph[T]:
        """Build graph from edge iterable.

        Args:
            edges: Iterable of (from, to) tuples (list, set, frozenset, generator)
            extra_nodes: Additional isolated nodes to include

        Returns:
            DiGraph with all edges and nodes

        Time: O(E) where E is number of edges
        """
        forward: dict[T, set[T]] = {}
        reverse: dict[T, set[T]] = {}
        nodes: set[T] = set()

        for from_node, to_node in edges:
            nodes.add(from_node)
            nodes.add(to_node)
            forward.setdefault(from_node, set()).add(to_node)
            reverse.setdefault(to_node, set()).add(from_node)

        if extra_nodes is not None:
            nodes.update(extra_nodes)

        return cls(
            forward={k: frozenset(v) for k, v in forward.items()},
            reverse={k: frozenset(v) for k, v in reverse.items()},
            nodes=frozenset(nodes),
        )

    @classmethod
    def empty(cls) -> DiGraph[T]:
        """Create empty graph with no nodes or edges."""
        return cls(forward={}, reverse={}, nodes=frozenset())


# =============================================================================
# GRAPH ALGORITHMS - Using stdlib graphlib (Python 3.9+)
# =============================================================================


def detect_cycles[T](graph: DiGraph[T]) -> tuple[frozenset[T], ...]:
    """Detect cycles in directed graph using graphlib.TopologicalSorter.

    Uses stdlib graphlib which provides CycleError with cycle nodes.

    Args:
        graph: Directed graph to check

    Returns:
        Empty tuple if no cycles.
        Tuple of frozensets, each containing nodes in a cycle.

    Note:
        graphlib.TopologicalSorter only returns ONE cycle when multiple exist.
        For full cycle enumeration, a more complex algorithm (Tarjan's) would be needed.
        For architecture validation, detecting ANY cycle is sufficient.
    """
    if graph.node_count == 0:
        return ()

    # Convert to adjacency dict for graphlib
    # graphlib expects: node -> iterable of dependencies (predecessors)
    # But we have: node -> successors (what node depends on)
    # For cycle detection, we need to reverse: node -> what depends on it
    # Actually, TopologicalSorter expects predecessors (dependencies)
    # forward[a] = {b} means a -> b (a calls b), so b depends on a being defined
    # For topological sort of call order: we want b before a (callee before caller)
    # So we pass forward as-is: successors are "dependencies"
    adjacency: dict[T, set[T]] = {}
    for node in graph.nodes:
        adjacency[node] = set(graph.successors(node))

    ts: TopologicalSorter[T] = TopologicalSorter(adjacency)
    try:
        # static_order() raises CycleError if cycles exist
        tuple(ts.static_order())
        return ()
    except CycleError as e:
        # e.args[1] contains the cycle as a list
        # The list shows the path: [a, b, c, a] where a->b->c->a
        cycle_path = e.args[1]
        # Convert to frozenset of unique nodes in cycle
        cycle_nodes = frozenset(cycle_path)
        return (cycle_nodes,)


def topological_order[T](graph: DiGraph[T]) -> tuple[T, ...] | None:
    """Get topological ordering of graph using graphlib.TopologicalSorter.

    Uses stdlib graphlib for efficient topological sort.

    Args:
        graph: Directed graph to sort

    Returns:
        Tuple of nodes in topological order (dependencies first).
        None if graph contains cycles.
    """
    if graph.node_count == 0:
        return ()

    # Build adjacency dict for graphlib
    adjacency: dict[T, set[T]] = {}
    for node in graph.nodes:
        adjacency[node] = set(graph.successors(node))

    ts: TopologicalSorter[T] = TopologicalSorter(adjacency)
    try:
        return tuple(ts.static_order())
    except CycleError:
        return None
