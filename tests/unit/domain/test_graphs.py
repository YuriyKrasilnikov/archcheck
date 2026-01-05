"""Tests for domain/graphs.py.

Tests:
- CallEdge invariants (count >= 1)
- CallEdge immutability
- CallEdge equality based on caller/callee
- CallGraph immutability and structure
"""

import pytest

from archcheck.domain.events import EventType, Location
from archcheck.domain.graphs import (
    AnalysisResult,
    CallEdge,
    CallGraph,
    FilterConfig,
    ObjectFlow,
    ObjectLifecycle,
)
from tests.factories import (
    make_call_event,
    make_create_event,
    make_destroy_event,
    make_location,
    make_return_event,
    make_tracking_result,
)


class TestCallEdge:
    """Tests for CallEdge."""

    def test_valid_edge_creation(self) -> None:
        """CallEdge created with valid count >= 1."""
        caller = Location(file="a.py", line=10, func="foo")
        callee = Location(file="b.py", line=20, func="bar")
        edge = CallEdge(caller=caller, callee=callee, count=1)

        assert edge.caller == caller
        assert edge.callee == callee
        assert edge.count == 1

    def test_count_greater_than_one(self) -> None:
        """CallEdge allows count > 1."""
        caller = Location(file="a.py", line=10, func="foo")
        callee = Location(file="b.py", line=20, func="bar")
        edge = CallEdge(caller=caller, callee=callee, count=5)

        assert edge.count == 5

    def test_count_zero_raises(self) -> None:
        """CallEdge with count=0 raises ValueError (FAIL-FIRST)."""
        caller = Location(file="a.py", line=10, func="foo")
        callee = Location(file="b.py", line=20, func="bar")

        with pytest.raises(ValueError, match="count must be >= 1"):
            CallEdge(caller=caller, callee=callee, count=0)

    def test_count_negative_raises(self) -> None:
        """CallEdge with negative count raises ValueError (FAIL-FIRST)."""
        caller = Location(file="a.py", line=10, func="foo")
        callee = Location(file="b.py", line=20, func="bar")

        with pytest.raises(ValueError, match="count must be >= 1"):
            CallEdge(caller=caller, callee=callee, count=-1)

    def test_frozen_immutable(self) -> None:
        """CallEdge is frozen (immutable)."""
        caller = Location(file="a.py", line=10, func="foo")
        callee = Location(file="b.py", line=20, func="bar")
        edge = CallEdge(caller=caller, callee=callee, count=1)

        with pytest.raises(AttributeError):
            edge.count = 2  # type: ignore[misc]

    def test_equality(self) -> None:
        """CallEdge equality based on all fields."""
        caller = Location(file="a.py", line=10, func="foo")
        callee = Location(file="b.py", line=20, func="bar")

        edge1 = CallEdge(caller=caller, callee=callee, count=1)
        edge2 = CallEdge(caller=caller, callee=callee, count=1)
        edge3 = CallEdge(caller=caller, callee=callee, count=2)

        assert edge1 == edge2
        assert edge1 != edge3

    def test_hashable(self) -> None:
        """CallEdge is hashable (can be used in frozenset)."""
        caller = Location(file="a.py", line=10, func="foo")
        callee = Location(file="b.py", line=20, func="bar")
        edge = CallEdge(caller=caller, callee=callee, count=1)

        # Should not raise
        edge_set = frozenset({edge})
        assert edge in edge_set


class TestCallGraph:
    """Tests for CallGraph."""

    def test_empty_graph(self) -> None:
        """CallGraph can be empty."""
        graph = CallGraph(edges=frozenset(), unmatched=())

        assert len(graph.edges) == 0
        assert len(graph.unmatched) == 0

    def test_graph_with_edges(self) -> None:
        """CallGraph stores edges."""
        caller = make_location(file="a.py", line=10, func="foo")
        callee = make_location(file="b.py", line=20, func="bar")
        edge = CallEdge(caller=caller, callee=callee, count=1)

        graph = CallGraph(edges=frozenset({edge}), unmatched=())

        assert edge in graph.edges
        assert len(graph.edges) == 1

    def test_graph_with_unmatched(self) -> None:
        """CallGraph tracks unmatched events (Data Completeness)."""
        orphan_call = make_call_event(func="orphan")
        orphan_return = make_return_event(func="orphan")

        graph = CallGraph(edges=frozenset(), unmatched=(orphan_call, orphan_return))

        assert len(graph.unmatched) == 2
        assert orphan_call in graph.unmatched
        assert orphan_return in graph.unmatched

    def test_frozen_immutable(self) -> None:
        """CallGraph is frozen (immutable)."""
        graph = CallGraph(edges=frozenset(), unmatched=())

        with pytest.raises(AttributeError):
            graph.edges = frozenset()  # type: ignore[misc]

    def test_edges_is_frozenset(self) -> None:
        """CallGraph.edges is frozenset (immutable)."""
        caller = make_location(file="a.py", line=10, func="foo")
        callee = make_location(file="b.py", line=20, func="bar")
        edge = CallEdge(caller=caller, callee=callee, count=1)

        graph = CallGraph(edges=frozenset({edge}), unmatched=())

        assert isinstance(graph.edges, frozenset)

    def test_unmatched_is_tuple(self) -> None:
        """CallGraph.unmatched is tuple (immutable)."""
        orphan = make_call_event(func="orphan")
        graph = CallGraph(edges=frozenset(), unmatched=(orphan,))

        assert isinstance(graph.unmatched, tuple)


class TestObjectLifecycle:
    """Tests for ObjectLifecycle."""

    def test_lifecycle_with_create_only(self) -> None:
        """ObjectLifecycle with create but no destroy (still alive)."""
        create = make_create_event(obj_id=100, type_name="Foo")
        lifecycle = ObjectLifecycle(
            obj_id=100,
            type_name="Foo",
            created=create,
            destroyed=None,
            locations=(),
        )

        assert lifecycle.obj_id == 100
        assert lifecycle.type_name == "Foo"
        assert lifecycle.created == create
        assert lifecycle.destroyed is None
        assert lifecycle.locations == ()

    def test_lifecycle_with_destroy(self) -> None:
        """ObjectLifecycle with both create and destroy."""
        create = make_create_event(obj_id=100, type_name="Foo")
        destroy = make_destroy_event(obj_id=100, type_name="Foo")
        lifecycle = ObjectLifecycle(
            obj_id=100,
            type_name="Foo",
            created=create,
            destroyed=destroy,
            locations=(),
        )

        assert lifecycle.destroyed == destroy

    def test_lifecycle_with_locations(self) -> None:
        """ObjectLifecycle tracks where object was passed."""
        create = make_create_event(obj_id=100, type_name="Foo")
        loc1 = make_location(file="a.py", line=10, func="func1")
        loc2 = make_location(file="b.py", line=20, func="func2")

        lifecycle = ObjectLifecycle(
            obj_id=100,
            type_name="Foo",
            created=create,
            destroyed=None,
            locations=(loc1, loc2),
        )

        assert len(lifecycle.locations) == 2
        assert loc1 in lifecycle.locations
        assert loc2 in lifecycle.locations

    def test_mismatched_obj_id_raises(self) -> None:
        """ObjectLifecycle with mismatched destroy obj_id raises (FAIL-FIRST)."""
        create = make_create_event(obj_id=100, type_name="Foo")
        destroy = make_destroy_event(obj_id=999, type_name="Foo")  # wrong id

        with pytest.raises(ValueError, match="obj_id mismatch"):
            ObjectLifecycle(
                obj_id=100,
                type_name="Foo",
                created=create,
                destroyed=destroy,
                locations=(),
            )

    def test_frozen_immutable(self) -> None:
        """ObjectLifecycle is frozen (immutable)."""
        create = make_create_event(obj_id=100, type_name="Foo")
        lifecycle = ObjectLifecycle(
            obj_id=100,
            type_name="Foo",
            created=create,
            destroyed=None,
            locations=(),
        )

        with pytest.raises(AttributeError):
            lifecycle.destroyed = None  # type: ignore[misc]


class TestObjectFlow:
    """Tests for ObjectFlow."""

    def test_empty_flow(self) -> None:
        """ObjectFlow can be empty."""
        flow = ObjectFlow(objects={}, orphan_destroys=())

        assert len(flow.objects) == 0
        assert len(flow.orphan_destroys) == 0

    def test_flow_with_objects(self) -> None:
        """ObjectFlow stores object lifecycles."""
        create = make_create_event(obj_id=100, type_name="Foo")
        lifecycle = ObjectLifecycle(
            obj_id=100,
            type_name="Foo",
            created=create,
            destroyed=None,
            locations=(),
        )

        flow = ObjectFlow(objects={100: lifecycle}, orphan_destroys=())

        assert 100 in flow.objects
        assert flow.objects[100] == lifecycle

    def test_flow_with_orphan_destroys(self) -> None:
        """ObjectFlow tracks orphan destroys (Data Completeness)."""
        orphan = make_destroy_event(obj_id=999, type_name="Unknown")

        flow = ObjectFlow(objects={}, orphan_destroys=(orphan,))

        assert len(flow.orphan_destroys) == 1
        assert orphan in flow.orphan_destroys

    def test_frozen_immutable(self) -> None:
        """ObjectFlow is frozen (immutable)."""
        flow = ObjectFlow(objects={}, orphan_destroys=())

        with pytest.raises(AttributeError):
            flow.objects = {}  # type: ignore[misc]

    def test_orphan_destroys_is_tuple(self) -> None:
        """ObjectFlow.orphan_destroys is tuple (immutable)."""
        orphan = make_destroy_event(obj_id=999, type_name="Unknown")
        flow = ObjectFlow(objects={}, orphan_destroys=(orphan,))

        assert isinstance(flow.orphan_destroys, tuple)


class TestFilterConfig:
    """Tests for FilterConfig."""

    def test_default_values(self) -> None:
        """FilterConfig has sensible defaults (all optional)."""
        config = FilterConfig()

        assert config.include_paths == ()
        assert config.exclude_paths == ()
        assert config.include_types is None

    def test_custom_include_paths(self) -> None:
        """FilterConfig accepts include_paths."""
        config = FilterConfig(include_paths=("src/**", "lib/**"))

        assert config.include_paths == ("src/**", "lib/**")

    def test_custom_exclude_paths(self) -> None:
        """FilterConfig accepts exclude_paths."""
        config = FilterConfig(exclude_paths=("**/.venv/**", "**/test_*"))

        assert config.exclude_paths == ("**/.venv/**", "**/test_*")

    def test_custom_include_types(self) -> None:
        """FilterConfig accepts include_types."""
        types = frozenset({EventType.CALL, EventType.RETURN})
        config = FilterConfig(include_types=types)

        assert config.include_types == types

    def test_all_fields_configurable(self) -> None:
        """All FilterConfig fields can be set (No Special Cases)."""
        config = FilterConfig(
            include_paths=("src/**",),
            exclude_paths=("**/test_*",),
            include_types=frozenset({EventType.CALL}),
        )

        assert config.include_paths == ("src/**",)
        assert config.exclude_paths == ("**/test_*",)
        assert config.include_types == frozenset({EventType.CALL})

    def test_frozen_immutable(self) -> None:
        """FilterConfig is frozen (immutable)."""
        config = FilterConfig()

        with pytest.raises(AttributeError):
            config.include_paths = ()  # type: ignore[misc]


class TestAnalysisResult:
    """Tests for AnalysisResult."""

    def test_stores_all_components(self) -> None:
        """AnalysisResult stores filtered result, call graph, and object flow."""
        filtered = make_tracking_result()
        call_graph = CallGraph(edges=frozenset(), unmatched=())
        object_flow = ObjectFlow(objects={}, orphan_destroys=())

        result = AnalysisResult(
            filtered=filtered,
            call_graph=call_graph,
            object_flow=object_flow,
        )

        assert result.filtered == filtered
        assert result.call_graph == call_graph
        assert result.object_flow == object_flow

    def test_frozen_immutable(self) -> None:
        """AnalysisResult is frozen (immutable)."""
        result = AnalysisResult(
            filtered=make_tracking_result(),
            call_graph=CallGraph(edges=frozenset(), unmatched=()),
            object_flow=ObjectFlow(objects={}, orphan_destroys=()),
        )

        with pytest.raises(AttributeError):
            result.filtered = make_tracking_result()  # type: ignore[misc]
