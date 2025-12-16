"""Tests for domain/model/runtime_call_graph.py."""

from pathlib import Path
from types import MappingProxyType

import pytest

from archcheck.domain.model.call_site import CallSite
from archcheck.domain.model.lib_call_site import LibCallSite
from archcheck.domain.model.runtime_call_graph import (
    FrozenRuntimeCallGraph,
    RuntimeCallGraph,
)


def make_call_site(module: str = "app.main", function: str = "run", line: int = 1) -> CallSite:
    """Create a valid CallSite for tests."""
    return CallSite(module=module, function=function, line=line, file=Path("test.py"))


def make_lib_call_site(lib_name: str = "requests", function: str = "get") -> LibCallSite:
    """Create a valid LibCallSite for tests."""
    return LibCallSite(lib_name=lib_name, function=function)


class TestFrozenRuntimeCallGraphEmpty:
    """Tests for FrozenRuntimeCallGraph.empty() factory."""

    def test_empty_returns_instance(self) -> None:
        """empty() returns FrozenRuntimeCallGraph instance."""
        result = FrozenRuntimeCallGraph.empty()
        assert isinstance(result, FrozenRuntimeCallGraph)

    def test_empty_has_no_edges(self) -> None:
        """empty() creates graph with no edges."""
        result = FrozenRuntimeCallGraph.empty()
        assert result.edge_count == 0

    def test_empty_has_no_lib_edges(self) -> None:
        """empty() creates graph with no library edges."""
        result = FrozenRuntimeCallGraph.empty()
        assert result.lib_edge_count == 0

    def test_empty_has_no_called_functions(self) -> None:
        """empty() creates graph with no called functions."""
        result = FrozenRuntimeCallGraph.empty()
        assert result.called_functions == frozenset()

    def test_empty_edges_is_mapping_proxy(self) -> None:
        """empty() edges is MappingProxyType (immutable)."""
        result = FrozenRuntimeCallGraph.empty()
        assert isinstance(result.edges, MappingProxyType)

    def test_empty_lib_edges_is_mapping_proxy(self) -> None:
        """empty() lib_edges is MappingProxyType (immutable)."""
        result = FrozenRuntimeCallGraph.empty()
        assert isinstance(result.lib_edges, MappingProxyType)

    def test_empty_total_calls_is_zero(self) -> None:
        """empty() has zero total calls."""
        result = FrozenRuntimeCallGraph.empty()
        assert result.total_calls == 0


class TestFrozenRuntimeCallGraphInvariants:
    """Tests for FrozenRuntimeCallGraph FAIL-FIRST validation."""

    def test_edges_with_callee_not_in_called_functions_raises(self) -> None:
        """edges containing callee not in called_functions raises ValueError."""
        caller = make_call_site("app.main", "run", 1)
        callee = make_call_site("app.helper", "do_work", 10)

        with pytest.raises(ValueError, match="not in called_functions"):
            FrozenRuntimeCallGraph(
                edges=MappingProxyType({(caller, callee): 1}),
                lib_edges=MappingProxyType({}),
                called_functions=frozenset(),  # Missing callee!
            )

    def test_valid_graph_with_callee_in_called_functions(self) -> None:
        """Graph with callee in called_functions is valid."""
        caller = make_call_site("app.main", "run", 1)
        callee = make_call_site("app.helper", "do_work", 10)

        graph = FrozenRuntimeCallGraph(
            edges=MappingProxyType({(caller, callee): 1}),
            lib_edges=MappingProxyType({}),
            called_functions=frozenset({callee}),
        )

        assert graph.edge_count == 1


class TestRuntimeCallGraphFreeze:
    """Tests for RuntimeCallGraph.freeze()."""

    def test_freeze_returns_frozen_graph(self) -> None:
        """freeze() returns FrozenRuntimeCallGraph."""
        graph = RuntimeCallGraph()
        frozen = graph.freeze()
        assert isinstance(frozen, FrozenRuntimeCallGraph)

    def test_freeze_empty_graph(self) -> None:
        """freeze() on empty graph returns empty frozen graph."""
        graph = RuntimeCallGraph()
        frozen = graph.freeze()
        assert frozen.edge_count == 0

    def test_freeze_captures_recorded_edges(self) -> None:
        """freeze() captures edges recorded via record_edge()."""
        graph = RuntimeCallGraph()
        caller = make_call_site("app.main", "run", 1)
        callee = make_call_site("app.helper", "do_work", 10)

        graph.record_edge(caller, callee)
        frozen = graph.freeze()

        assert frozen.edge_count == 1
        assert (caller, callee) in frozen.edges

    def test_freeze_captures_lib_edges(self) -> None:
        """freeze() captures lib edges recorded via record_lib_edge()."""
        graph = RuntimeCallGraph()
        caller = make_call_site("app.main", "run", 1)
        lib = make_lib_call_site("requests", "get")

        graph.record_lib_edge(caller, lib)
        frozen = graph.freeze()

        assert frozen.lib_edge_count == 1
        assert (caller, lib) in frozen.lib_edges

    def test_freeze_aggregates_call_counts(self) -> None:
        """freeze() aggregates multiple calls to same edge."""
        graph = RuntimeCallGraph()
        caller = make_call_site("app.main", "run", 1)
        callee = make_call_site("app.helper", "do_work", 10)

        graph.record_edge(caller, callee)
        graph.record_edge(caller, callee)
        graph.record_edge(caller, callee)
        frozen = graph.freeze()

        assert frozen.edges[(caller, callee)] == 3
