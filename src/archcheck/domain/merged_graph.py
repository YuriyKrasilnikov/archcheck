"""Domain layer: merged call graph (static + runtime).

Combines static analysis from AST with runtime tracking.
Indexes computed once in __post_init__ for O(1) lookups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from archcheck.domain.exceptions import MissingEdgeSourceError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from archcheck.domain.graphs import CallEdge
    from archcheck.domain.static_graph import StaticCallEdge


class EdgeNature(Enum):
    """Classification of merged edge source.

    STATIC_ONLY:  visible in AST, not called at runtime
    RUNTIME_ONLY: called at runtime, not visible in AST (dynamic)
    BOTH:         visible in AST and called at runtime
    PARAMETRIC:   HOF/callback (caller doesn't know callee statically)
    """

    STATIC_ONLY = "STATIC_ONLY"
    RUNTIME_ONLY = "RUNTIME_ONLY"
    BOTH = "BOTH"
    PARAMETRIC = "PARAMETRIC"


@dataclass(frozen=True, slots=True)
class MergedCallEdge:
    """Edge in merged call graph.

    At least one of static or runtime must be present.
    FQNs are canonical (same for both sources).

    Invariants (FAIL-FIRST):
        - static is not None OR runtime is not None
    """

    caller_fqn: str
    callee_fqn: str
    static: StaticCallEdge | None
    runtime: CallEdge | None
    nature: EdgeNature

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST if neither static nor runtime."""
        if self.static is None and self.runtime is None:
            raise MissingEdgeSourceError


@dataclass(frozen=True, slots=True)
class MergedCallGraph:
    """Merged call graph with precomputed indexes.

    edges: all merged edges
    nodes: all unique FQNs (caller + callee)
    by_caller: caller_fqn → set of callee_fqns
    by_callee: callee_fqn → set of caller_fqns
    by_nature: EdgeNature → edges with that nature

    Indexes computed once in __post_init__ for O(1) lookups.
    """

    edges: tuple[MergedCallEdge, ...]
    nodes: frozenset[str] = field(default_factory=frozenset)
    by_caller: Mapping[str, frozenset[str]] = field(default_factory=dict)
    by_callee: Mapping[str, frozenset[str]] = field(default_factory=dict)
    by_nature: Mapping[EdgeNature, tuple[MergedCallEdge, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Compute indexes from edges."""
        # Collect nodes
        nodes: set[str] = set()
        for edge in self.edges:
            nodes.add(edge.caller_fqn)
            nodes.add(edge.callee_fqn)

        # Build by_caller: caller → callees
        by_caller: dict[str, set[str]] = {}
        for edge in self.edges:
            by_caller.setdefault(edge.caller_fqn, set()).add(edge.callee_fqn)

        # Build by_callee: callee → callers
        by_callee: dict[str, set[str]] = {}
        for edge in self.edges:
            by_callee.setdefault(edge.callee_fqn, set()).add(edge.caller_fqn)

        # Build by_nature: nature → edges
        by_nature: dict[EdgeNature, list[MergedCallEdge]] = {}
        for edge in self.edges:
            by_nature.setdefault(edge.nature, []).append(edge)

        # Freeze and assign via object.__setattr__ (frozen dataclass)
        object.__setattr__(self, "nodes", frozenset(nodes))
        object.__setattr__(
            self,
            "by_caller",
            {k: frozenset(v) for k, v in by_caller.items()},
        )
        object.__setattr__(
            self,
            "by_callee",
            {k: frozenset(v) for k, v in by_callee.items()},
        )
        object.__setattr__(
            self,
            "by_nature",
            {k: tuple(v) for k, v in by_nature.items()},
        )

    @classmethod
    def empty(cls) -> MergedCallGraph:
        """Create empty graph for tests or initial state."""
        return cls(edges=())
