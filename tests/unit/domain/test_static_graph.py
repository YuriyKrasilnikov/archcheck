"""Tests for domain/static_graph.py.

Tests:
- CallType enum exhaustive
- StaticCallEdge immutability
- UnresolvedCall structure
- StaticCallGraph Data Completeness (unresolved tracked)
"""

import pytest

from archcheck.domain.events import Location
from archcheck.domain.static_graph import (
    CallType,
    StaticCallEdge,
    StaticCallGraph,
    UnresolvedCall,
)


class TestCallType:
    """Tests for CallType enum."""

    def test_all_types_exist(self) -> None:
        """All call types represented."""
        assert CallType.DIRECT.value == "DIRECT"
        assert CallType.METHOD.value == "METHOD"
        assert CallType.SUPER.value == "SUPER"
        assert CallType.DECORATOR.value == "DECORATOR"
        assert CallType.CONSTRUCTOR.value == "CONSTRUCTOR"

    def test_exhaustive_iteration(self) -> None:
        """Enum has exactly 5 members."""
        assert len(list(CallType)) == 5


class TestStaticCallEdge:
    """Tests for StaticCallEdge."""

    def test_direct_call(self) -> None:
        """Direct call: foo()."""
        loc = Location(file="app/service.py", line=10, func="handle")
        edge = StaticCallEdge(
            caller_fqn="app.service.handle",
            callee_fqn="app.utils.helper",
            location=loc,
            call_type=CallType.DIRECT,
        )

        assert edge.caller_fqn == "app.service.handle"
        assert edge.callee_fqn == "app.utils.helper"
        assert edge.location == loc
        assert edge.call_type == CallType.DIRECT

    def test_method_call(self) -> None:
        """Method call: self.process()."""
        loc = Location(file="app/service.py", line=15, func="handle")
        edge = StaticCallEdge(
            caller_fqn="app.service.Service.handle",
            callee_fqn="app.service.Service.process",
            location=loc,
            call_type=CallType.METHOD,
        )

        assert edge.call_type == CallType.METHOD

    def test_super_call(self) -> None:
        """Super call: super().__init__()."""
        loc = Location(file="app/models.py", line=5, func="__init__")
        edge = StaticCallEdge(
            caller_fqn="app.models.User.__init__",
            callee_fqn="app.models.BaseModel.__init__",
            location=loc,
            call_type=CallType.SUPER,
        )

        assert edge.call_type == CallType.SUPER

    def test_decorator_call(self) -> None:
        """Decorator: @route."""
        loc = Location(file="app/api.py", line=10, func="handler")
        edge = StaticCallEdge(
            caller_fqn="app.api.handler",
            callee_fqn="app.decorators.route",
            location=loc,
            call_type=CallType.DECORATOR,
        )

        assert edge.call_type == CallType.DECORATOR

    def test_constructor_call(self) -> None:
        """Constructor: User()."""
        loc = Location(file="app/service.py", line=20, func="create_user")
        edge = StaticCallEdge(
            caller_fqn="app.service.create_user",
            callee_fqn="app.models.User.__init__",
            location=loc,
            call_type=CallType.CONSTRUCTOR,
        )

        assert edge.call_type == CallType.CONSTRUCTOR

    def test_frozen_immutable(self) -> None:
        """StaticCallEdge is frozen."""
        loc = Location(file="test.py", line=1, func="f")
        edge = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )

        with pytest.raises(AttributeError):
            edge.caller_fqn = "other"  # type: ignore[misc]

    def test_hashable(self) -> None:
        """StaticCallEdge is hashable."""
        loc = Location(file="test.py", line=1, func="f")
        edge = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )

        edge_set = frozenset({edge})
        assert edge in edge_set


class TestUnresolvedCall:
    """Tests for UnresolvedCall."""

    def test_unresolved_import_not_found(self) -> None:
        """Unresolved: import not found."""
        loc = Location(file="app/service.py", line=10, func="handle")
        unresolved = UnresolvedCall(
            caller_fqn="app.service.handle",
            callee_name="unknown_func",
            location=loc,
            reason="import not found",
        )

        assert unresolved.caller_fqn == "app.service.handle"
        assert unresolved.callee_name == "unknown_func"
        assert unresolved.reason == "import not found"

    def test_unresolved_dynamic(self) -> None:
        """Unresolved: dynamic call."""
        loc = Location(file="app/service.py", line=15, func="handle")
        unresolved = UnresolvedCall(
            caller_fqn="app.service.handle",
            callee_name="getattr(obj, name)()",
            location=loc,
            reason="dynamic",
        )

        assert unresolved.reason == "dynamic"

    def test_frozen_immutable(self) -> None:
        """UnresolvedCall is frozen."""
        loc = Location(file="test.py", line=1, func="f")
        unresolved = UnresolvedCall(
            caller_fqn="test.f",
            callee_name="unknown",
            location=loc,
            reason="not found",
        )

        with pytest.raises(AttributeError):
            unresolved.reason = "other"  # type: ignore[misc]


class TestStaticCallGraph:
    """Tests for StaticCallGraph."""

    def test_empty_graph(self) -> None:
        """Empty graph."""
        graph = StaticCallGraph(edges=(), unresolved=())

        assert graph.edges == ()
        assert graph.unresolved == ()

    def test_graph_with_edges(self) -> None:
        """Graph with edges."""
        loc = Location(file="test.py", line=1, func="f")
        edge = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        graph = StaticCallGraph(edges=(edge,), unresolved=())

        assert len(graph.edges) == 1
        assert graph.edges[0] == edge

    def test_graph_with_unresolved(self) -> None:
        """Graph tracks unresolved (Data Completeness)."""
        loc = Location(file="test.py", line=1, func="f")
        unresolved = UnresolvedCall(
            caller_fqn="test.f",
            callee_name="unknown",
            location=loc,
            reason="not found",
        )
        graph = StaticCallGraph(edges=(), unresolved=(unresolved,))

        assert len(graph.unresolved) == 1
        assert graph.unresolved[0] == unresolved

    def test_graph_mixed(self) -> None:
        """Graph with edges and unresolved."""
        loc = Location(file="test.py", line=1, func="f")
        edge = StaticCallEdge(
            caller_fqn="test.f",
            callee_fqn="test.g",
            location=loc,
            call_type=CallType.DIRECT,
        )
        unresolved = UnresolvedCall(
            caller_fqn="test.f",
            callee_name="unknown",
            location=loc,
            reason="not found",
        )
        graph = StaticCallGraph(edges=(edge,), unresolved=(unresolved,))

        assert len(graph.edges) == 1
        assert len(graph.unresolved) == 1

    def test_frozen_immutable(self) -> None:
        """StaticCallGraph is frozen."""
        graph = StaticCallGraph(edges=(), unresolved=())

        with pytest.raises(AttributeError):
            graph.edges = ()  # type: ignore[misc]

    def test_empty_classmethod(self) -> None:
        """StaticCallGraph.empty() for convenience."""
        graph = StaticCallGraph.empty()

        assert graph.edges == ()
        assert graph.unresolved == ()
