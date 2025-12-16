"""Tests for EdgeQuery and EdgeAssertion in presentation/api/dsl.py."""

from pathlib import Path

import pytest

from archcheck.domain.exceptions.base import ArchCheckError
from archcheck.domain.exceptions.violation import ArchitectureViolationError
from archcheck.domain.model.call_instance import CallInstance
from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.edge_nature import EdgeNature
from archcheck.domain.model.entry_points import EntryPointCategories
from archcheck.domain.model.function_edge import FunctionEdge
from archcheck.domain.model.location import Location
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from archcheck.domain.model.module import Module
from archcheck.presentation.api.dsl import ArchCheck, EdgeAssertion, EdgeQuery


def make_location(line: int = 1) -> Location:
    """Create a valid Location."""
    return Location(file=Path("test.py"), line=line, column=0)


def make_call_instance(line: int = 1) -> CallInstance:
    """Create a valid CallInstance."""
    return CallInstance(
        location=make_location(line),
        call_type=CallType.FUNCTION,
        count=1,
    )


def make_edge(
    caller: str,
    callee: str,
    nature: EdgeNature = EdgeNature.DIRECT,
) -> FunctionEdge:
    """Create a valid FunctionEdge."""
    return FunctionEdge(
        caller_fqn=caller,
        callee_fqn=callee,
        nature=nature,
        calls=(make_call_instance(),),
    )


def make_graph(*edges: FunctionEdge) -> MergedCallGraph:
    """Create a MergedCallGraph with given edges."""
    nodes = set()
    for e in edges:
        nodes.add(e.caller_fqn)
        nodes.add(e.callee_fqn)

    return MergedCallGraph(
        nodes=frozenset(nodes),
        edges=edges,
        lib_edges=(),
        hidden_deps=frozenset(),
        entry_points=EntryPointCategories.empty(),
    )


def make_codebase() -> Codebase:
    """Create empty codebase."""
    return Codebase(root_path=Path("/test"), root_package="myapp")


class TestArchCheckEdges:
    """Tests for ArchCheck.edges()."""

    def test_edges_without_graph_raises(self) -> None:
        """edges() without graph raises ArchCheckError."""
        codebase = make_codebase()
        arch = ArchCheck(codebase)

        with pytest.raises(ArchCheckError, match="MergedCallGraph not available"):
            arch.edges()

    def test_edges_with_graph_returns_query(self) -> None:
        """edges() with graph returns EdgeQuery."""
        codebase = make_codebase()
        graph = make_graph()
        arch = ArchCheck(codebase, graph)

        result = arch.edges()

        assert isinstance(result, EdgeQuery)


class TestEdgeQueryFilters:
    """Tests for EdgeQuery filter methods."""

    def test_from_layer_filters(self) -> None:
        """from_layer() filters by caller layer."""
        e1 = make_edge("myapp.domain.foo", "myapp.domain.bar")
        e2 = make_edge("myapp.infra.baz", "myapp.domain.bar")
        graph = make_graph(e1, e2)

        result = EdgeQuery.create(graph).from_layer("domain").execute()

        assert len(result) == 1
        assert result[0].caller_fqn == "myapp.domain.foo"

    def test_to_layer_filters(self) -> None:
        """to_layer() filters by callee layer."""
        e1 = make_edge("myapp.domain.foo", "myapp.domain.bar")
        e2 = make_edge("myapp.domain.foo", "myapp.infra.baz")
        graph = make_graph(e1, e2)

        result = EdgeQuery.create(graph).to_layer("infra").execute()

        assert len(result) == 1
        assert result[0].callee_fqn == "myapp.infra.baz"

    def test_crossing_boundary_filters(self) -> None:
        """crossing_boundary() filters to cross-layer edges."""
        e1 = make_edge("myapp.domain.foo", "myapp.domain.bar")  # same layer
        e2 = make_edge("myapp.domain.foo", "myapp.infra.baz")  # cross layer
        graph = make_graph(e1, e2)

        result = EdgeQuery.create(graph).crossing_boundary().execute()

        assert len(result) == 1
        assert result[0].callee_fqn == "myapp.infra.baz"

    def test_with_nature_filters(self) -> None:
        """with_nature() filters by edge nature."""
        e1 = make_edge("myapp.a", "myapp.b", EdgeNature.DIRECT)
        e2 = make_edge("myapp.c", "myapp.d", EdgeNature.INHERITED)
        graph = make_graph(e1, e2)

        result = EdgeQuery.create(graph).with_nature(EdgeNature.INHERITED).execute()

        assert len(result) == 1
        assert result[0].nature == EdgeNature.INHERITED

    def test_direct_only_filters(self) -> None:
        """direct_only() filters to DIRECT edges."""
        e1 = make_edge("myapp.a", "myapp.b", EdgeNature.DIRECT)
        e2 = make_edge("myapp.c", "myapp.d", EdgeNature.PARAMETRIC)
        graph = make_graph(e1, e2)

        result = EdgeQuery.create(graph).direct_only().execute()

        assert len(result) == 1
        assert result[0].nature == EdgeNature.DIRECT

    def test_that_filters_by_predicate(self) -> None:
        """that() filters by custom predicate."""
        e1 = make_edge("myapp.foo", "myapp.bar")
        e2 = make_edge("myapp.baz", "myapp.qux")
        graph = make_graph(e1, e2)

        result = EdgeQuery.create(graph).that(lambda e: "foo" in e.caller_fqn).execute()

        assert len(result) == 1
        assert result[0].caller_fqn == "myapp.foo"

    def test_chained_filters(self) -> None:
        """Multiple filters can be chained."""
        e1 = make_edge("myapp.domain.foo", "myapp.infra.bar", EdgeNature.DIRECT)
        e2 = make_edge("myapp.domain.foo", "myapp.domain.baz", EdgeNature.DIRECT)
        e3 = make_edge("myapp.infra.qux", "myapp.domain.bar", EdgeNature.DIRECT)
        graph = make_graph(e1, e2, e3)

        result = (
            EdgeQuery.create(graph)
            .from_layer("domain")
            .crossing_boundary()
            .direct_only()
            .execute()
        )

        assert len(result) == 1
        assert result[0].caller_fqn == "myapp.domain.foo"
        assert result[0].callee_fqn == "myapp.infra.bar"


class TestEdgeQueryShould:
    """Tests for EdgeQuery.should() transition."""

    def test_should_returns_assertion(self) -> None:
        """should() returns EdgeAssertion."""
        graph = make_graph()

        result = EdgeQuery.create(graph).should()

        assert isinstance(result, EdgeAssertion)

    def test_should_passes_filtered_edges(self) -> None:
        """should() passes filtered edges to assertion."""
        e1 = make_edge("myapp.domain.foo", "myapp.domain.bar")
        e2 = make_edge("myapp.infra.baz", "myapp.infra.qux")
        graph = make_graph(e1, e2)

        assertion = EdgeQuery.create(graph).from_layer("domain").should()

        assert assertion.edge_count == 1


class TestEdgeAssertionNotCrossBoundary:
    """Tests for EdgeAssertion.not_cross_boundary()."""

    def test_no_violation_when_same_layer(self) -> None:
        """No violation when edge stays in same layer."""
        e = make_edge("myapp.domain.foo", "myapp.domain.bar")
        assertion = EdgeAssertion(_edges=(e,))

        violations = assertion.not_cross_boundary().collect()

        assert len(violations) == 0

    def test_violation_when_crosses_layer(self) -> None:
        """Violation when edge crosses layer boundary."""
        e = make_edge("myapp.domain.foo", "myapp.infra.bar")
        assertion = EdgeAssertion(_edges=(e,))

        violations = assertion.not_cross_boundary().collect()

        assert len(violations) == 1
        assert "not_cross_boundary" in violations[0].rule_name


class TestEdgeAssertionBeAllowed:
    """Tests for EdgeAssertion.be_allowed()."""

    def test_none_allowed_imports_raises(self) -> None:
        """None allowed_imports raises TypeError."""
        assertion = EdgeAssertion(_edges=())

        with pytest.raises(TypeError, match="allowed_imports must not be None"):
            assertion.be_allowed(None)  # type: ignore[arg-type]

    def test_no_violation_when_same_layer(self) -> None:
        """No violation when edge in same layer."""
        e = make_edge("myapp.domain.foo", "myapp.domain.bar")
        assertion = EdgeAssertion(_edges=(e,))
        allowed = {"domain": frozenset()}  # empty, but same layer OK

        violations = assertion.be_allowed(allowed).collect()

        assert len(violations) == 0

    def test_no_violation_when_allowed(self) -> None:
        """No violation when cross-layer edge is allowed."""
        e = make_edge("myapp.application.foo", "myapp.domain.bar")
        assertion = EdgeAssertion(_edges=(e,))
        allowed = {"application": frozenset({"domain"})}

        violations = assertion.be_allowed(allowed).collect()

        assert len(violations) == 0

    def test_violation_when_not_allowed(self) -> None:
        """Violation when cross-layer edge not allowed."""
        e = make_edge("myapp.domain.foo", "myapp.infra.bar")
        assertion = EdgeAssertion(_edges=(e,))
        allowed = {"domain": frozenset()}  # domain can't call anything

        violations = assertion.be_allowed(allowed).collect()

        assert len(violations) == 1
        assert "be_allowed" in violations[0].rule_name


class TestEdgeAssertionExecution:
    """Tests for EdgeAssertion execution methods."""

    def test_assert_check_raises_on_violations(self) -> None:
        """assert_check() raises ArchitectureViolationError on violations."""
        e = make_edge("myapp.domain.foo", "myapp.infra.bar")
        assertion = EdgeAssertion(_edges=(e,))

        with pytest.raises(ArchitectureViolationError):
            assertion.not_cross_boundary().assert_check()

    def test_assert_check_passes_on_no_violations(self) -> None:
        """assert_check() does not raise when no violations."""
        e = make_edge("myapp.domain.foo", "myapp.domain.bar")
        assertion = EdgeAssertion(_edges=(e,))

        # Should not raise
        assertion.not_cross_boundary().assert_check()

    def test_is_valid_true_on_no_violations(self) -> None:
        """is_valid() returns True when no violations."""
        e = make_edge("myapp.domain.foo", "myapp.domain.bar")
        assertion = EdgeAssertion(_edges=(e,))

        assert assertion.not_cross_boundary().is_valid()

    def test_is_valid_false_on_violations(self) -> None:
        """is_valid() returns False when violations exist."""
        e = make_edge("myapp.domain.foo", "myapp.infra.bar")
        assertion = EdgeAssertion(_edges=(e,))

        assert not assertion.not_cross_boundary().is_valid()


class TestEdgeFluentChaining:
    """Tests for full fluent chain with edges."""

    def test_full_chain_pass(self) -> None:
        """Full fluent chain passes with valid architecture."""
        e1 = make_edge("myapp.domain.foo", "myapp.domain.bar")
        e2 = make_edge("myapp.application.svc", "myapp.domain.bar")
        graph = make_graph(e1, e2)
        codebase = make_codebase()
        arch = ArchCheck(codebase, graph)

        allowed = {
            "domain": frozenset(),
            "application": frozenset({"domain"}),
        }

        # Should not raise
        (
            arch.edges()
            .direct_only()
            .should()
            .be_allowed(allowed)
            .assert_check()
        )

    def test_full_chain_fail(self) -> None:
        """Full fluent chain fails with invalid architecture."""
        e = make_edge("myapp.domain.foo", "myapp.infra.bar")
        graph = make_graph(e)
        codebase = make_codebase()
        arch = ArchCheck(codebase, graph)

        with pytest.raises(ArchitectureViolationError):
            (
                arch.edges()
                .should()
                .not_cross_boundary()
                .assert_check()
            )
