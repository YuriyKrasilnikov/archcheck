"""Merged call graph combining AST and Runtime analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from archcheck.domain.model.edge_nature import EdgeNature
from archcheck.domain.model.entry_points import EntryPointCategories
from archcheck.domain.model.hidden_dep import HiddenDep

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from archcheck.domain.model.function_edge import FunctionEdge
    from archcheck.domain.model.lib_edge import LibEdge


@dataclass(frozen=True, slots=True)
class MergedCallGraph:
    """Indexed call graph with O(1) access.

    Immutable aggregate combining static analysis (AST) with runtime analysis.
    All indexes are precomputed in __post_init__ for O(1) query performance.

    Primary Storage (source of truth):
        nodes: All function FQNs in the graph
        edges: All function-to-function edges
        lib_edges: All function-to-library edges
        hidden_deps: Runtime-only dependencies (DYNAMIC type only)
        entry_points: Categorized entry points

    Precomputed Indexes:
        _idx_by_pair: O(1) lookup by (caller_fqn, callee_fqn)
        _idx_by_caller: O(1) lookup of callees by caller
        _idx_by_callee: O(1) lookup of callers by callee
        _idx_by_nature: Edges grouped by EdgeNature
        _idx_direct: Precomputed DIRECT edges (boundary-relevant)
    """

    # === PRIMARY STORAGE ===
    nodes: frozenset[str]
    edges: tuple[FunctionEdge, ...]
    lib_edges: tuple[LibEdge, ...]
    hidden_deps: frozenset[HiddenDep]
    entry_points: EntryPointCategories

    # === PRECOMPUTED INDEXES (built in __post_init__) ===
    _idx_by_pair: Mapping[tuple[str, str], FunctionEdge] = field(
        default_factory=dict, repr=False, compare=False
    )
    _idx_by_caller: Mapping[str, frozenset[str]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _idx_by_callee: Mapping[str, frozenset[str]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _idx_by_nature: Mapping[EdgeNature, tuple[FunctionEdge, ...]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _idx_direct: tuple[FunctionEdge, ...] = field(default_factory=tuple, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Build indexes and validate. FAIL-FIRST."""
        # === VALIDATION ===
        seen_pairs: set[tuple[str, str]] = set()
        for edge in self.edges:
            # All edge endpoints must be in nodes
            if edge.caller_fqn not in self.nodes:
                raise ValueError(f"edge caller '{edge.caller_fqn}' not in nodes")
            if edge.callee_fqn not in self.nodes:
                raise ValueError(f"edge callee '{edge.callee_fqn}' not in nodes")
            # No duplicate edges
            pair = edge.fqn_pair
            if pair in seen_pairs:
                raise ValueError(f"duplicate edge: {pair}")
            seen_pairs.add(pair)

        # All lib_edge callers must be in nodes
        for lib_edge in self.lib_edges:
            if lib_edge.caller_fqn not in self.nodes:
                raise ValueError(f"lib edge caller '{lib_edge.caller_fqn}' not in nodes")

        # All entry points must be in nodes
        for fqn in self.entry_points.all_entry_points:
            if fqn not in self.nodes:
                raise ValueError(f"entry point '{fqn}' not in nodes")

        # === BUILD INDEXES ===
        idx_by_pair: dict[tuple[str, str], FunctionEdge] = {}
        idx_by_caller: dict[str, set[str]] = {}
        idx_by_callee: dict[str, set[str]] = {}
        idx_by_nature: dict[EdgeNature, list[FunctionEdge]] = {n: [] for n in EdgeNature}
        idx_direct: list[FunctionEdge] = []

        for edge in self.edges:
            # by_pair index
            idx_by_pair[edge.fqn_pair] = edge

            # by_caller index
            idx_by_caller.setdefault(edge.caller_fqn, set()).add(edge.callee_fqn)

            # by_callee index
            idx_by_callee.setdefault(edge.callee_fqn, set()).add(edge.caller_fqn)

            # by_nature index
            idx_by_nature[edge.nature].append(edge)

            # direct index
            if edge.nature == EdgeNature.DIRECT:
                idx_direct.append(edge)

        # Set indexes using object.__setattr__ (frozen dataclass workaround)
        object.__setattr__(self, "_idx_by_pair", MappingProxyType(idx_by_pair))
        object.__setattr__(
            self,
            "_idx_by_caller",
            MappingProxyType({k: frozenset(v) for k, v in idx_by_caller.items()}),
        )
        object.__setattr__(
            self,
            "_idx_by_callee",
            MappingProxyType({k: frozenset(v) for k, v in idx_by_callee.items()}),
        )
        object.__setattr__(
            self,
            "_idx_by_nature",
            MappingProxyType({k: tuple(v) for k, v in idx_by_nature.items()}),
        )
        object.__setattr__(self, "_idx_direct", tuple(idx_direct))

    # === O(1) ACCESSORS ===

    def get_edge(self, caller_fqn: str, callee_fqn: str) -> FunctionEdge | None:
        """Get edge by FQN pair. O(1)."""
        return self._idx_by_pair.get((caller_fqn, callee_fqn))

    def get_callees_of(self, fqn: str) -> frozenset[str]:
        """Get FQNs of all functions called by fqn. O(1)."""
        return self._idx_by_caller.get(fqn, frozenset())

    def get_callers_of(self, fqn: str) -> frozenset[str]:
        """Get FQNs of all functions that call fqn. O(1)."""
        return self._idx_by_callee.get(fqn, frozenset())

    def edges_by_nature(self, nature: EdgeNature) -> tuple[FunctionEdge, ...]:
        """Get all edges with given nature. O(1)."""
        return self._idx_by_nature.get(nature, ())

    # === PRECOMPUTED VIEWS ===

    @property
    def direct_edges(self) -> tuple[FunctionEdge, ...]:
        """DIRECT edges only (boundary-relevant). O(1)."""
        return self._idx_direct

    @property
    def edge_pairs(self) -> frozenset[tuple[str, str]]:
        """All (caller_fqn, callee_fqn) pairs for cycle detection. O(1)."""
        return frozenset(self._idx_by_pair.keys())

    # === COUNTS ===

    @property
    def edge_count(self) -> int:
        """Number of function edges."""
        return len(self.edges)

    @property
    def lib_edge_count(self) -> int:
        """Number of library edges."""
        return len(self.lib_edges)

    @property
    def hidden_dep_count(self) -> int:
        """Number of hidden dependencies."""
        return len(self.hidden_deps)

    @property
    def node_count(self) -> int:
        """Number of nodes in graph."""
        return len(self.nodes)

    # === FACTORY ===

    @classmethod
    def empty(cls) -> MergedCallGraph:
        """Create empty merged call graph."""
        return cls(
            nodes=frozenset(),
            edges=(),
            lib_edges=(),
            hidden_deps=frozenset(),
            entry_points=EntryPointCategories.empty(),
        )

    @classmethod
    def build(
        cls,
        nodes: frozenset[str],
        edges: Iterable[FunctionEdge],
        lib_edges: Iterable[LibEdge],
        hidden_deps: Iterable[HiddenDep],
        entry_points: EntryPointCategories,
    ) -> MergedCallGraph:
        """Build graph from iterables. Validates and builds indexes."""
        return cls(
            nodes=nodes,
            edges=tuple(edges),
            lib_edges=tuple(lib_edges),
            hidden_deps=frozenset(hidden_deps),
            entry_points=entry_points,
        )
