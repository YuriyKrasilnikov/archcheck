"""Tests for AnalyzerService.

Tests:
- filter(): applies FilterConfig to TrackingResult
- build_call_graph(): constructs CallGraph from CALL/RETURN events
- build_object_flow(): constructs ObjectFlow from CREATE/DESTROY events
- analyze(): orchestrates all analysis steps
"""

import pytest

from archcheck.application.services.analyzer import AnalyzerService
from archcheck.domain.events import (
    ArgInfo,
    CallEvent,
    CreateEvent,
    DestroyEvent,
    EventType,
    Location,
    TrackingResult,
)
from archcheck.domain.graphs import AnalysisResult, FilterConfig
from tests.factories import (
    make_call_event,
    make_create_event,
    make_destroy_event,
    make_output_error,
    make_return_event,
    make_tracking_result,
)


class TestAnalyzerServiceFilter:
    """Tests for AnalyzerService.filter()."""

    def test_filter_empty_config_returns_all(self) -> None:
        """Empty FilterConfig returns all events unchanged."""
        events = (
            make_call_event(file="src/main.py"),
            make_return_event(file="src/main.py"),
            make_create_event(file="lib/utils.py"),
        )
        result = make_tracking_result(events=events)
        config = FilterConfig()

        service = AnalyzerService()
        filtered = service.filter(result, config)

        assert len(filtered.events) == 3
        assert filtered.events == events

    def test_filter_include_types(self) -> None:
        """FilterConfig.include_types filters by event type."""
        events = (
            make_call_event(),
            make_return_event(),
            make_create_event(),
            make_destroy_event(),
        )
        result = make_tracking_result(events=events)
        config = FilterConfig(include_types=frozenset({EventType.CALL, EventType.RETURN}))

        service = AnalyzerService()
        filtered = service.filter(result, config)

        assert len(filtered.events) == 2
        assert all(isinstance(e, (type(events[0]), type(events[1]))) for e in filtered.events)

    def test_filter_include_paths(self) -> None:
        """FilterConfig.include_paths filters by file path."""
        events = (
            make_call_event(file="src/main.py"),
            make_call_event(file="lib/utils.py"),
            make_call_event(file="tests/test_main.py"),
        )
        result = make_tracking_result(events=events)
        config = FilterConfig(include_paths=("src/*",))

        service = AnalyzerService()
        filtered = service.filter(result, config)

        assert len(filtered.events) == 1
        assert filtered.events[0].location.file == "src/main.py"

    def test_filter_exclude_paths(self) -> None:
        """FilterConfig.exclude_paths excludes by file path."""
        events = (
            make_call_event(file="src/main.py"),
            make_call_event(file="src/.venv/lib.py"),
            make_call_event(file="tests/test_main.py"),
        )
        result = make_tracking_result(events=events)
        config = FilterConfig(exclude_paths=("*.venv*", "*test_*"))

        service = AnalyzerService()
        filtered = service.filter(result, config)

        assert len(filtered.events) == 1
        assert filtered.events[0].location.file == "src/main.py"

    def test_filter_combined(self) -> None:
        """FilterConfig with multiple filters applies all."""
        events = (
            make_call_event(file="src/main.py"),
            make_return_event(file="src/main.py"),
            make_create_event(file="src/main.py"),
            make_call_event(file="lib/utils.py"),
        )
        result = make_tracking_result(events=events)
        config = FilterConfig(
            include_types=frozenset({EventType.CALL}),
            include_paths=("src/*",),
        )

        service = AnalyzerService()
        filtered = service.filter(result, config)

        assert len(filtered.events) == 1
        assert filtered.events[0].location.file == "src/main.py"

    def test_filter_preserves_output_errors(self) -> None:
        """filter() preserves output_errors from original result."""
        errors = (make_output_error(),)
        result = TrackingResult(events=(), output_errors=errors)
        config = FilterConfig()

        service = AnalyzerService()
        filtered = service.filter(result, config)

        assert filtered.output_errors == errors

    def test_filter_path_not_applied_to_create_destroy(self) -> None:
        """Path filters do NOT apply to CREATE/DESTROY.

        Object IDs are global: object created in file A, destroyed in file B.
        Filtering by path would break ObjectFlow invariants (DESTROY without CREATE).
        """
        events = (
            make_call_event(file="src/main.py"),  # CALL src/ → keep
            make_call_event(file="lib/utils.py"),  # CALL lib/ → filtered
            make_create_event(file="lib/utils.py"),  # CREATE lib/ → keep
            make_destroy_event(file="lib/utils.py"),  # DESTROY lib/ → keep
        )
        result = make_tracking_result(events=events)
        config = FilterConfig(include_paths=("src/*",))

        service = AnalyzerService()
        filtered = service.filter(result, config)

        # 1 CALL (src/) + 1 CREATE + 1 DESTROY = 3
        assert len(filtered.events) == 3
        # Verify exact events kept
        assert sum(1 for e in filtered.events if isinstance(e, CallEvent)) == 1
        assert sum(1 for e in filtered.events if isinstance(e, CreateEvent)) == 1
        assert sum(1 for e in filtered.events if isinstance(e, DestroyEvent)) == 1


class TestAnalyzerServiceBuildCallGraph:
    """Tests for AnalyzerService.build_call_graph()."""

    def test_empty_events(self) -> None:
        """Empty events produce empty graph."""
        result = make_tracking_result(events=())

        service = AnalyzerService()
        graph = service.build_call_graph(result)

        assert len(graph.edges) == 0
        assert len(graph.unmatched) == 0

    def test_matched_call_return(self) -> None:
        """Matched CALL/RETURN creates edge."""
        caller_loc = Location(file="a.py", line=10, func="caller")
        callee_loc = Location(file="b.py", line=20, func="callee")

        events = (
            make_call_event(
                file="b.py",
                line=20,
                func="callee",
                caller_file="a.py",
                caller_line=10,
                caller_func="caller",
            ),
            make_return_event(file="b.py", line=20, func="callee"),
        )
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        graph = service.build_call_graph(result)

        assert len(graph.edges) == 1
        edge = next(iter(graph.edges))
        assert edge.caller == caller_loc
        assert edge.callee == callee_loc
        assert edge.count == 1
        assert len(graph.unmatched) == 0

    def test_duplicate_edges_increment_count(self) -> None:
        """Multiple same calls increment edge count."""
        events = (
            make_call_event(file="b.py", func="callee", caller_file="a.py", caller_func="caller"),
            make_return_event(file="b.py", func="callee"),
            make_call_event(file="b.py", func="callee", caller_file="a.py", caller_func="caller"),
            make_return_event(file="b.py", func="callee"),
        )
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        graph = service.build_call_graph(result)

        assert len(graph.edges) == 1
        edge = next(iter(graph.edges))
        assert edge.count == 2

    def test_unmatched_return(self) -> None:
        """RETURN without CALL tracked in unmatched (Data Completeness)."""
        events = (make_return_event(func="orphan"),)
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        graph = service.build_call_graph(result)

        assert len(graph.edges) == 0
        assert len(graph.unmatched) == 1
        assert isinstance(graph.unmatched[0], type(events[0]))

    def test_unmatched_call(self) -> None:
        """CALL without RETURN tracked in unmatched (Data Completeness)."""
        events = (make_call_event(func="orphan"),)
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        graph = service.build_call_graph(result)

        assert len(graph.edges) == 0
        assert len(graph.unmatched) == 1

    def test_self_loop_filtered(self) -> None:
        """Self-loops (caller == callee) are filtered out."""
        events = (
            make_call_event(
                file="a.py",
                line=10,
                func="recursive",
                caller_file="a.py",
                caller_line=10,
                caller_func="recursive",
            ),
            make_return_event(file="a.py", line=10, func="recursive"),
        )
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        graph = service.build_call_graph(result)

        assert len(graph.edges) == 0
        assert len(graph.unmatched) == 0

    def test_no_caller_info(self) -> None:
        """CALL without caller info doesn't create edge."""
        events = (
            make_call_event(func="callee", caller_file=None, caller_line=0, caller_func=None),
            make_return_event(func="callee"),
        )
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        graph = service.build_call_graph(result)

        # No edge because caller is None
        assert len(graph.edges) == 0


class TestAnalyzerServiceBuildObjectFlow:
    """Tests for AnalyzerService.build_object_flow()."""

    def test_empty_events(self) -> None:
        """Empty events produce empty flow."""
        result = make_tracking_result(events=())

        service = AnalyzerService()
        flow = service.build_object_flow(result)

        assert len(flow.objects) == 0
        assert len(flow.orphan_destroys) == 0

    def test_create_only(self) -> None:
        """CREATE without DESTROY creates lifecycle with destroyed=None."""
        events = (make_create_event(obj_id=100, type_name="Foo"),)
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        flow = service.build_object_flow(result)

        assert len(flow.objects) == 1
        assert 100 in flow.objects
        lifecycle = flow.objects[100]
        assert lifecycle.obj_id == 100
        assert lifecycle.type_name == "Foo"
        assert lifecycle.destroyed is None

    def test_create_and_destroy(self) -> None:
        """CREATE and DESTROY creates complete lifecycle."""
        events = (
            make_create_event(obj_id=100, type_name="Foo"),
            make_destroy_event(obj_id=100, type_name="Foo"),
        )
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        flow = service.build_object_flow(result)

        assert len(flow.objects) == 1
        lifecycle = flow.objects[100]
        assert lifecycle.destroyed is not None
        assert lifecycle.destroyed.obj_id == 100

    def test_orphan_destroy(self) -> None:
        """DESTROY without CREATE tracked in orphan_destroys (Data Completeness)."""
        events = (make_destroy_event(obj_id=999, type_name="Unknown"),)
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        flow = service.build_object_flow(result)

        assert len(flow.objects) == 0
        assert len(flow.orphan_destroys) == 1
        assert flow.orphan_destroys[0].obj_id == 999

    def test_duplicate_create_raises(self) -> None:
        """Multiple CREATE with same obj_id raises (FAIL-FIRST)."""
        events = (
            make_create_event(obj_id=100, type_name="Foo"),
            make_create_event(obj_id=100, type_name="Foo"),  # duplicate
        )
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        with pytest.raises(ValueError, match="Duplicate CREATE"):
            service.build_object_flow(result)

    def test_locations_tracked_from_call_args(self) -> None:
        """Object locations tracked from CALL.args."""
        obj_id = 100
        events = (
            make_create_event(obj_id=obj_id, type_name="Foo"),
            make_call_event(
                file="a.py",
                line=10,
                func="use_foo",
                args=(ArgInfo(name="foo", obj_id=obj_id, type_name="Foo"),),
            ),
            make_call_event(
                file="b.py",
                line=20,
                func="another_use",
                args=(ArgInfo(name="obj", obj_id=obj_id, type_name="Foo"),),
            ),
        )
        result = make_tracking_result(events=events)

        service = AnalyzerService()
        flow = service.build_object_flow(result)

        lifecycle = flow.objects[obj_id]
        assert len(lifecycle.locations) == 2
        assert lifecycle.locations[0].file == "a.py"
        assert lifecycle.locations[1].file == "b.py"


class TestAnalyzerServiceAnalyze:
    """Tests for AnalyzerService.analyze()."""

    def test_analyze_returns_analysis_result(self) -> None:
        """analyze() returns AnalysisResult with all components."""
        events = (
            make_call_event(file="src/main.py", caller_file="src/app.py", caller_func="main"),
            make_return_event(file="src/main.py"),
            make_create_event(obj_id=100, type_name="Foo"),
        )
        result = make_tracking_result(events=events)
        config = FilterConfig()

        service = AnalyzerService()
        analysis = service.analyze(result, config)

        assert isinstance(analysis, AnalysisResult)
        assert analysis.filtered is not None
        assert analysis.call_graph is not None
        assert analysis.object_flow is not None

    def test_analyze_applies_filter(self) -> None:
        """analyze() applies filter config before building graphs."""
        events = (
            make_call_event(file="src/main.py"),
            make_call_event(file="tests/test.py"),
        )
        result = make_tracking_result(events=events)
        config = FilterConfig(include_paths=("src/*",))

        service = AnalyzerService()
        analysis = service.analyze(result, config)

        # Only src/ events in filtered result
        assert len(analysis.filtered.events) == 1
        assert analysis.filtered.events[0].location.file == "src/main.py"

    def test_analyze_builds_call_graph(self) -> None:
        """analyze() builds call graph from filtered events."""
        events = (
            make_call_event(file="a.py", func="callee", caller_file="b.py", caller_func="caller"),
            make_return_event(file="a.py", func="callee"),
        )
        result = make_tracking_result(events=events)
        config = FilterConfig()

        service = AnalyzerService()
        analysis = service.analyze(result, config)

        assert len(analysis.call_graph.edges) == 1

    def test_analyze_builds_object_flow(self) -> None:
        """analyze() builds object flow from filtered events."""
        events = (
            make_create_event(obj_id=100, type_name="Foo"),
            make_destroy_event(obj_id=100, type_name="Foo"),
        )
        result = make_tracking_result(events=events)
        config = FilterConfig()

        service = AnalyzerService()
        analysis = service.analyze(result, config)

        assert len(analysis.object_flow.objects) == 1
        assert 100 in analysis.object_flow.objects
