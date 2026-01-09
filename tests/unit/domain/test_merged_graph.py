"""Tests for domain/merged_graph.py.

Tests:
- EdgeNature enum exhaustive
- MergedCallEdge invariant (static OR runtime present)
- MergedCallGraph indexes computed
"""

import pytest

from archcheck.domain.events import Location
from archcheck.domain.graphs import CallEdge
from archcheck.domain.merged_graph import EdgeNature, MergedCallEdge, MergedCallGraph
from archcheck.domain.static_graph import CallType, StaticCallEdge


class TestEdgeNature:
    """Tests for EdgeNature enum."""

    def test_all_natures_exist(self) -> None:
        """All edge natures represented."""
        assert EdgeNature.STATIC_ONLY.value == "STATIC_ONLY"
        assert EdgeNature.RUNTIME_ONLY.value == "RUNTIME_ONLY"
        assert EdgeNature.BOTH.value == "BOTH"
        assert EdgeNature.PARAMETRIC.value == "PARAMETRIC"

    def test_exhaustive_iteration(self) -> None:
        """Enum has exactly 4 members."""
        assert len(list(EdgeNature)) == 4


class TestMergedCallEdge:
    """Tests for MergedCallEdge."""

    def test_static_only(self) -> None:
        """Edge from static analysis only."""
        loc = Location(file="test.py", line=10, func="f")
        static = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        edge = MergedCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            static=static,
            runtime=None,
            nature=EdgeNature.STATIC_ONLY,
        )

        assert edge.caller_fqn == "test.f"
        assert edge.callee_fqn == "test.g"
        assert edge.static == static
        assert edge.runtime is None
        assert edge.nature == EdgeNature.STATIC_ONLY

    def test_runtime_only(self) -> None:
        """Edge from runtime tracking only."""
        caller_loc = Location(file="test.py", line=5, func="f")
        callee_loc = Location(file="test.py", line=15, func="g")
        runtime = CallEdge(caller=caller_loc, callee=callee_loc, count=1)
        edge = MergedCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            static=None,
            runtime=runtime,
            nature=EdgeNature.RUNTIME_ONLY,
        )

        assert edge.static is None
        assert edge.runtime == runtime
        assert edge.nature == EdgeNature.RUNTIME_ONLY

    def test_both(self) -> None:
        """Edge from both static and runtime."""
        loc = Location(file="test.py", line=10, func="f")
        static = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        caller_loc = Location(file="test.py", line=5, func="f")
        callee_loc = Location(file="test.py", line=15, func="g")
        runtime = CallEdge(caller=caller_loc, callee=callee_loc, count=3)
        edge = MergedCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            static=static,
            runtime=runtime,
            nature=EdgeNature.BOTH,
        )

        assert edge.static is not None
        assert edge.runtime is not None
        assert edge.nature == EdgeNature.BOTH

    def test_parametric(self) -> None:
        """Parametric edge (HOF/callback)."""
        caller_loc = Location(file="test.py", line=5, func="process")
        callee_loc = Location(file="test.py", line=20, func="transform")
        runtime = CallEdge(caller=caller_loc, callee=callee_loc, count=10)
        edge = MergedCallEdge(
            caller_fqn="test.process",
            callee_fqn="test.transform",
            static=None,
            runtime=runtime,
            nature=EdgeNature.PARAMETRIC,
        )

        assert edge.nature == EdgeNature.PARAMETRIC

    def test_neither_static_nor_runtime_raises(self) -> None:
        """Neither static nor runtime raises ValueError (FAIL-FIRST)."""
        with pytest.raises(ValueError, match="at least one of static or runtime"):
            MergedCallEdge(
                caller_fqn="test.f",
                callee_fqn="test.g",
                static=None,
                runtime=None,
                nature=EdgeNature.BOTH,
            )

    def test_frozen_immutable(self) -> None:
        """MergedCallEdge is frozen."""
        loc = Location(file="test.py", line=10, func="f")
        static = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        edge = MergedCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            static=static,
            runtime=None,
            nature=EdgeNature.STATIC_ONLY,
        )

        with pytest.raises(AttributeError):
            edge.nature = EdgeNature.BOTH  # type: ignore[misc]


class TestMergedCallGraph:
    """Tests for MergedCallGraph."""

    def test_empty_graph(self) -> None:
        """Empty graph via classmethod."""
        graph = MergedCallGraph.empty()

        assert graph.edges == ()
        assert graph.nodes == frozenset()
        assert graph.by_caller == {}
        assert graph.by_callee == {}
        assert graph.by_nature == {}

    def test_graph_with_edges(self) -> None:
        """Graph computes indexes."""
        loc = Location(file="test.py", line=10, func="f")
        static = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        edge = MergedCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            static=static,
            runtime=None,
            nature=EdgeNature.STATIC_ONLY,
        )
        graph = MergedCallGraph(edges=(edge,))

        assert len(graph.edges) == 1
        assert "test.f" in graph.nodes
        assert "test.g" in graph.nodes

    def test_by_caller_index(self) -> None:
        """by_caller index maps caller → callees."""
        loc = Location(file="test.py", line=10, func="f")
        static1 = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        static2 = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.h",
            location=loc,
            call_type=CallType.DIRECT,
        )
        edge1 = MergedCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            static=static1,
            runtime=None,
            nature=EdgeNature.STATIC_ONLY,
        )
        edge2 = MergedCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.h",
            static=static2,
            runtime=None,
            nature=EdgeNature.STATIC_ONLY,
        )
        graph = MergedCallGraph(edges=(edge1, edge2))

        assert "test.f" in graph.by_caller
        assert graph.by_caller["test.f"] == frozenset({"test.g", "test.h"})

    def test_by_callee_index(self) -> None:
        """by_callee index maps callee → callers."""
        loc = Location(file="test.py", line=10, func="f")
        static1 = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        static2 = StaticCallEdge(
            caller_fqn="test.h",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        edge1 = MergedCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            static=static1,
            runtime=None,
            nature=EdgeNature.STATIC_ONLY,
        )
        edge2 = MergedCallEdge(
            caller_fqn="test.h",
            callee_fqn="test.g",
            static=static2,
            runtime=None,
            nature=EdgeNature.STATIC_ONLY,
        )
        graph = MergedCallGraph(edges=(edge1, edge2))

        assert "test.g" in graph.by_callee
        assert graph.by_callee["test.g"] == frozenset({"test.f", "test.h"})

    def test_by_nature_index(self) -> None:
        """by_nature index maps nature → edges."""
        loc = Location(file="test.py", line=10, func="f")
        static = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        caller_loc = Location(file="test.py", line=5, func="h")
        callee_loc = Location(file="test.py", line=25, func="i")
        runtime = CallEdge(caller=caller_loc, callee=callee_loc, count=1)

        edge1 = MergedCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            static=static,
            runtime=None,
            nature=EdgeNature.STATIC_ONLY,
        )
        edge2 = MergedCallEdge(
            caller_fqn="test.h",
            callee_fqn="test.i",
            static=None,
            runtime=runtime,
            nature=EdgeNature.RUNTIME_ONLY,
        )
        graph = MergedCallGraph(edges=(edge1, edge2))

        assert EdgeNature.STATIC_ONLY in graph.by_nature
        assert EdgeNature.RUNTIME_ONLY in graph.by_nature
        assert len(graph.by_nature[EdgeNature.STATIC_ONLY]) == 1
        assert len(graph.by_nature[EdgeNature.RUNTIME_ONLY]) == 1

    def test_frozen_immutable(self) -> None:
        """MergedCallGraph is frozen."""
        graph = MergedCallGraph.empty()

        with pytest.raises(AttributeError):
            graph.edges = ()  # type: ignore[misc]
