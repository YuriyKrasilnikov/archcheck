"""Tests for domain/model/graph.py."""

import pytest

from archcheck.domain.model.graph import DiGraph


class TestDiGraphCreation:
    """Tests for valid DiGraph creation."""

    def test_empty_graph(self) -> None:
        g = DiGraph.empty()
        assert g.nodes == frozenset()
        assert g.forward == {}
        assert g.reverse == {}

    def test_single_node_no_edges(self) -> None:
        g = DiGraph(
            forward={},
            reverse={},
            nodes=frozenset({"a"}),
        )
        assert "a" in g.nodes
        assert g.node_count == 1
        assert g.edge_count == 0

    def test_single_edge(self) -> None:
        g = DiGraph(
            forward={"a": frozenset({"b"})},
            reverse={"b": frozenset({"a"})},
            nodes=frozenset({"a", "b"}),
        )
        assert g.has_edge("a", "b")
        assert not g.has_edge("b", "a")
        assert g.edge_count == 1

    def test_multiple_edges(self) -> None:
        g = DiGraph(
            forward={
                "a": frozenset({"b", "c"}),
                "b": frozenset({"c"}),
            },
            reverse={
                "b": frozenset({"a"}),
                "c": frozenset({"a", "b"}),
            },
            nodes=frozenset({"a", "b", "c"}),
        )
        assert g.has_edge("a", "b")
        assert g.has_edge("a", "c")
        assert g.has_edge("b", "c")
        assert g.edge_count == 3

    def test_self_loop(self) -> None:
        g = DiGraph(
            forward={"a": frozenset({"a"})},
            reverse={"a": frozenset({"a"})},
            nodes=frozenset({"a"}),
        )
        assert g.has_edge("a", "a")

    def test_is_frozen(self) -> None:
        g = DiGraph.empty()
        with pytest.raises(AttributeError):
            g.nodes = frozenset({"x"})  # type: ignore[misc]


class TestDiGraphFailFirst:
    """Tests for FAIL-FIRST validation in DiGraph."""

    def test_forward_key_not_in_nodes_raises(self) -> None:
        with pytest.raises(ValueError, match="forward key 'a' not in nodes"):
            DiGraph(
                forward={"a": frozenset()},
                reverse={},
                nodes=frozenset(),
            )

    def test_successor_not_in_nodes_raises(self) -> None:
        with pytest.raises(ValueError, match="successor 'b' of 'a' not in nodes"):
            DiGraph(
                forward={"a": frozenset({"b"})},
                reverse={},
                nodes=frozenset({"a"}),
            )

    def test_reverse_key_not_in_nodes_raises(self) -> None:
        with pytest.raises(ValueError, match="reverse key 'b' not in nodes"):
            DiGraph(
                forward={},
                reverse={"b": frozenset()},
                nodes=frozenset(),
            )

    def test_predecessor_not_in_nodes_raises(self) -> None:
        with pytest.raises(ValueError, match="predecessor 'a' of 'b' not in nodes"):
            DiGraph(
                forward={},
                reverse={"b": frozenset({"a"})},
                nodes=frozenset({"b"}),
            )

    def test_inconsistent_forward_reverse_raises(self) -> None:
        # a→b in forward but missing in reverse
        with pytest.raises(ValueError, match="inconsistent.*a→b in forward"):
            DiGraph(
                forward={"a": frozenset({"b"})},
                reverse={},
                nodes=frozenset({"a", "b"}),
            )

    def test_inconsistent_reverse_forward_raises(self) -> None:
        # a→b in reverse but missing in forward
        with pytest.raises(ValueError, match="inconsistent.*a→b in reverse"):
            DiGraph(
                forward={},
                reverse={"b": frozenset({"a"})},
                nodes=frozenset({"a", "b"}),
            )


class TestDiGraphFromEdges:
    """Tests for DiGraph.from_edges class method."""

    def test_empty_edges(self) -> None:
        g = DiGraph.from_edges(iter([]))
        assert g.nodes == frozenset()
        assert g.edge_count == 0

    def test_single_edge(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b")]))
        assert g.nodes == frozenset({"a", "b"})
        assert g.has_edge("a", "b")
        assert not g.has_edge("b", "a")

    def test_multiple_edges(self) -> None:
        edges = [("a", "b"), ("a", "c"), ("b", "c")]
        g = DiGraph.from_edges(iter(edges))
        assert g.nodes == frozenset({"a", "b", "c"})
        assert g.has_edge("a", "b")
        assert g.has_edge("a", "c")
        assert g.has_edge("b", "c")
        assert g.edge_count == 3

    def test_with_extra_nodes(self) -> None:
        edges = [("a", "b")]
        g = DiGraph.from_edges(iter(edges), extra_nodes=frozenset({"c", "d"}))
        assert g.nodes == frozenset({"a", "b", "c", "d"})
        assert g.has_node("c")
        assert g.has_node("d")

    def test_duplicate_edges(self) -> None:
        # Same edge twice should not duplicate
        edges = [("a", "b"), ("a", "b")]
        g = DiGraph.from_edges(iter(edges))
        assert g.edge_count == 1


class TestDiGraphSuccessors:
    """Tests for DiGraph.successors method."""

    def test_existing_node(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b"), ("a", "c")]))
        assert g.successors("a") == frozenset({"b", "c"})

    def test_node_with_no_outgoing(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b")]))
        assert g.successors("b") == frozenset()

    def test_nonexistent_node(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b")]))
        assert g.successors("x") == frozenset()


class TestDiGraphPredecessors:
    """Tests for DiGraph.predecessors method."""

    def test_existing_node(self) -> None:
        g = DiGraph.from_edges(iter([("a", "c"), ("b", "c")]))
        assert g.predecessors("c") == frozenset({"a", "b"})

    def test_node_with_no_incoming(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b")]))
        assert g.predecessors("a") == frozenset()

    def test_nonexistent_node(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b")]))
        assert g.predecessors("x") == frozenset()


class TestDiGraphDegree:
    """Tests for DiGraph degree methods."""

    def test_out_degree(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b"), ("a", "c")]))
        assert g.out_degree("a") == 2
        assert g.out_degree("b") == 0

    def test_in_degree(self) -> None:
        g = DiGraph.from_edges(iter([("a", "c"), ("b", "c")]))
        assert g.in_degree("c") == 2
        assert g.in_degree("a") == 0


class TestDiGraphHasNode:
    """Tests for DiGraph.has_node method."""

    def test_existing_node(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b")]))
        assert g.has_node("a")
        assert g.has_node("b")

    def test_nonexistent_node(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b")]))
        assert not g.has_node("x")


class TestDiGraphCounts:
    """Tests for DiGraph count properties."""

    def test_node_count(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b"), ("a", "c")]))
        assert g.node_count == 3

    def test_edge_count(self) -> None:
        g = DiGraph.from_edges(iter([("a", "b"), ("a", "c"), ("b", "c")]))
        assert g.edge_count == 3

    def test_empty_counts(self) -> None:
        g = DiGraph.empty()
        assert g.node_count == 0
        assert g.edge_count == 0


# =============================================================================
# Tests for detect_cycles (graph algorithm using graphlib)
# =============================================================================


class TestDetectCycles:
    """Tests for detect_cycles function."""

    def test_no_cycles_empty_graph(self) -> None:
        from archcheck.domain.model.graph import detect_cycles

        g = DiGraph.empty()
        assert detect_cycles(g) == ()

    def test_no_cycles_linear(self) -> None:
        from archcheck.domain.model.graph import detect_cycles

        # a → b → c (no cycle)
        g = DiGraph.from_edges(iter([("a", "b"), ("b", "c")]))
        assert detect_cycles(g) == ()

    def test_no_cycles_tree(self) -> None:
        from archcheck.domain.model.graph import detect_cycles

        # a → b, a → c (tree, no cycle)
        g = DiGraph.from_edges(iter([("a", "b"), ("a", "c")]))
        assert detect_cycles(g) == ()

    def test_simple_cycle(self) -> None:
        from archcheck.domain.model.graph import detect_cycles

        # a → b → a (simple cycle)
        g = DiGraph.from_edges(iter([("a", "b"), ("b", "a")]))
        result = detect_cycles(g)
        assert len(result) == 1
        assert "a" in result[0]
        assert "b" in result[0]

    def test_self_loop(self) -> None:
        from archcheck.domain.model.graph import detect_cycles

        # a → a (self loop)
        g = DiGraph.from_edges(iter([("a", "a")]))
        result = detect_cycles(g)
        assert len(result) == 1
        assert "a" in result[0]

    def test_longer_cycle(self) -> None:
        from archcheck.domain.model.graph import detect_cycles

        # a → b → c → a (3-node cycle)
        g = DiGraph.from_edges(iter([("a", "b"), ("b", "c"), ("c", "a")]))
        result = detect_cycles(g)
        assert len(result) == 1
        assert {"a", "b", "c"} <= result[0]


# =============================================================================
# Tests for topological_order (graph algorithm using graphlib)
# =============================================================================


class TestTopologicalOrder:
    """Tests for topological_order function."""

    def test_empty_graph(self) -> None:
        from archcheck.domain.model.graph import topological_order

        g = DiGraph.empty()
        assert topological_order(g) == ()

    def test_linear_graph(self) -> None:
        from archcheck.domain.model.graph import topological_order

        # a → b → c
        g = DiGraph.from_edges(iter([("a", "b"), ("b", "c")]))
        result = topological_order(g)
        assert result is not None
        # c must come before b, b must come before a (dependencies first)
        assert result.index("c") < result.index("b")
        assert result.index("b") < result.index("a")

    def test_diamond_graph(self) -> None:
        from archcheck.domain.model.graph import topological_order

        # a → b, a → c, b → d, c → d (diamond)
        g = DiGraph.from_edges(iter([("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")]))
        result = topological_order(g)
        assert result is not None
        # d must come before b and c, b and c must come before a
        assert result.index("d") < result.index("b")
        assert result.index("d") < result.index("c")
        assert result.index("b") < result.index("a")
        assert result.index("c") < result.index("a")

    def test_cycle_returns_none(self) -> None:
        from archcheck.domain.model.graph import topological_order

        # a → b → a (cycle)
        g = DiGraph.from_edges(iter([("a", "b"), ("b", "a")]))
        assert topological_order(g) is None

    def test_isolated_nodes(self) -> None:
        from archcheck.domain.model.graph import topological_order

        # a → b, with isolated node c
        g = DiGraph.from_edges(iter([("a", "b")]), extra_nodes=frozenset({"c"}))
        result = topological_order(g)
        assert result is not None
        assert "a" in result
        assert "b" in result
        assert "c" in result
