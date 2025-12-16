"""Runtime call graph for Python 3.14 sys.monitoring analysis."""

from __future__ import annotations

import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from archcheck.domain.model.call_site import CallSite
from archcheck.domain.model.lib_call_site import LibCallSite


@dataclass(frozen=True, slots=True)
class FrozenRuntimeCallGraph:
    """Immutable snapshot of RuntimeCallGraph.

    Thread-safe immutable view of runtime call data.
    Created by RuntimeCallGraph.freeze().

    Attributes:
        edges: App→App edges with call counts
        lib_edges: App→Lib edges with call counts
        called_functions: All called CallSites
    """

    edges: Mapping[tuple[CallSite, CallSite], int]
    lib_edges: Mapping[tuple[CallSite, LibCallSite], int]
    called_functions: frozenset[CallSite]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        # All called_functions must appear in edges (as callee)
        callees_in_edges = {callee for _, callee in self.edges}
        if not callees_in_edges <= self.called_functions:
            missing = callees_in_edges - self.called_functions
            raise ValueError(f"edges contain callees not in called_functions: {missing}")

    @property
    def edge_count(self) -> int:
        """Total number of unique edges."""
        return len(self.edges)

    @property
    def lib_edge_count(self) -> int:
        """Total number of unique library edges."""
        return len(self.lib_edges)

    @property
    def total_calls(self) -> int:
        """Total number of calls (sum of all counts)."""
        return sum(self.edges.values()) + sum(self.lib_edges.values())

    @classmethod
    def empty(cls) -> FrozenRuntimeCallGraph:
        """Create empty graph for static-only analysis.

        Used when runtime collection is not available.

        Returns:
            Empty FrozenRuntimeCallGraph with no edges.
        """
        return cls(
            edges=MappingProxyType({}),
            lib_edges=MappingProxyType({}),
            called_functions=frozenset(),
        )


@dataclass(slots=True)
class RuntimeCallGraph:
    """Thread-safe mutable runtime call graph.

    Used during collection phase. Mutable, thread-safe.
    Call freeze() to get immutable snapshot.

    NOT frozen because it's a mutable collector.
    Thread-safety via Lock.
    """

    _edges: dict[tuple[CallSite, CallSite], int] = field(default_factory=dict)
    _lib_edges: dict[tuple[CallSite, LibCallSite], int] = field(default_factory=dict)
    _called_functions: set[CallSite] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_edge(self, caller: CallSite, callee: CallSite) -> None:
        """Record app→app call edge. Thread-safe.

        Args:
            caller: Calling function
            callee: Called function
        """
        with self._lock:
            key = (caller, callee)
            self._edges[key] = self._edges.get(key, 0) + 1
            self._called_functions.add(callee)

    def record_lib_edge(self, caller: CallSite, lib: LibCallSite) -> None:
        """Record app→lib call edge. Thread-safe.

        Args:
            caller: Calling function (app code)
            lib: Called library function
        """
        with self._lock:
            key = (caller, lib)
            self._lib_edges[key] = self._lib_edges.get(key, 0) + 1

    def freeze(self) -> FrozenRuntimeCallGraph:
        """Create immutable snapshot. Thread-safe.

        Returns:
            Immutable FrozenRuntimeCallGraph
        """
        with self._lock:
            return FrozenRuntimeCallGraph(
                edges=MappingProxyType(dict(self._edges)),
                lib_edges=MappingProxyType(dict(self._lib_edges)),
                called_functions=frozenset(self._called_functions),
            )

    @property
    def edge_count(self) -> int:
        """Current number of unique edges. Thread-safe."""
        with self._lock:
            return len(self._edges)

    @property
    def lib_edge_count(self) -> int:
        """Current number of unique library edges. Thread-safe."""
        with self._lock:
            return len(self._lib_edges)
