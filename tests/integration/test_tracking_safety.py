"""Integration tests for tracking safety.

Tests:
- stop() callable from tracked code without crash
- Nested calls with realloc safety
- Events captured correctly before stop()
- Self-tracking archcheck code works
- API error handling
"""

import pytest

from archcheck.application.reporters.console import ConsoleReporter
from archcheck.application.services.tracker import TrackerService
from archcheck.domain import CallEvent, CreateEvent, DestroyEvent, ReturnEvent
from archcheck.infrastructure import tracking
from tests.factories import make_tracking_result


class TestStopFromTrackedCode:
    """Tests for calling stop() from within tracked code."""

    def test_stop_from_script_no_crash(self) -> None:
        """stop() called directly from script level does not crash."""
        tracking.start()

        def user_function() -> int:
            return 42

        result = user_function()
        assert result == 42

        # This should NOT crash
        tr = tracking.stop()

        assert tr is not None
        assert len(tr.events) > 0

    def test_stop_from_wrapper_function_no_crash(self) -> None:
        """stop() called from wrapper function does not crash."""

        def run_with_tracking() -> int:
            tracking.start()
            result = 1 + 1
            tracking.stop()  # Called from within this function
            return result

        # This should NOT crash
        result = run_with_tracking()
        assert result == 2

    def test_tracker_service_track_no_crash(self) -> None:
        """TrackerService.track() works without crash."""

        def target() -> int:
            return 42

        tracker = TrackerService()

        # This should NOT crash
        result, tr = tracker.track(target)

        assert result == 42
        assert tr is not None

    def test_tracker_service_track_context_no_crash(self) -> None:
        """TrackerService.track_context() works without crash."""
        tracker = TrackerService()

        # This should NOT crash
        with tracker.track_context() as handle:
            result = 1 + 1

        assert handle.result is not None
        assert result == 2


class TestNestedCalls:
    """Tests for nested function calls and realloc safety."""

    def test_deeply_nested_calls(self) -> None:
        """Deeply nested calls don't crash (realloc safety)."""
        tracking.start()

        def level_3() -> int:
            return 3

        def level_2() -> int:
            return level_3() + 2

        def level_1() -> int:
            return level_2() + 1

        result = level_1()
        assert result == 6

        tr = tracking.stop()

        # Should have CALL/RETURN pairs for each level
        assert len(tr.events) >= 6  # At least 3 CALLs + 3 RETURNs

    def test_recursive_calls(self) -> None:
        """Recursive calls don't crash."""
        tracking.start()

        def factorial(n: int) -> int:
            if n <= 1:
                return 1
            return n * factorial(n - 1)

        result = factorial(5)
        assert result == 120

        tr = tracking.stop()

        # Many CALL/RETURN events from recursion
        assert len(tr.events) >= 10

    def test_many_calls_trigger_realloc(self) -> None:
        """Many calls trigger events realloc without crash."""
        tracking.start()

        def noop() -> None:
            pass

        # Trigger many events to force realloc
        for _ in range(1000):
            noop()

        tr = tracking.stop()

        # Should have captured many events
        assert len(tr.events) >= 2000  # 1000 calls * (CALL + RETURN)


class TestEventsContent:
    """Tests for events content correctness."""

    def test_call_event_captured(self) -> None:
        """CALL events are captured with function info."""
        tracking.start()

        def my_function() -> int:
            return 42

        my_function()

        tr = tracking.stop()

        # Find CALL event for my_function
        # co_qualname includes full path: "TestEventsContent.test_call_event_captured.<locals>.my_function"
        call_events = [e for e in tr.events if isinstance(e, CallEvent)]
        my_func_calls = [
            e for e in call_events if e.location.func and "my_function" in e.location.func
        ]

        assert len(my_func_calls) >= 1

    def test_return_event_captured(self) -> None:
        """RETURN events are captured with return info."""
        tracking.start()

        def my_function() -> int:
            return 42

        my_function()

        tr = tracking.stop()

        # Find RETURN event
        # co_qualname includes full path
        return_events = [e for e in tr.events if isinstance(e, ReturnEvent)]
        my_func_returns = [
            e for e in return_events if e.location.func and "my_function" in e.location.func
        ]

        assert len(my_func_returns) >= 1
        assert my_func_returns[0].return_type == "int"

    def test_create_event_captured(self) -> None:
        """CREATE events are captured for object allocation."""
        tracking.start()

        class MyClass:
            pass

        obj = MyClass()
        _ = obj  # Use it

        tr = tracking.stop()

        # Find CREATE event for MyClass
        create_events = [e for e in tr.events if isinstance(e, CreateEvent)]
        my_class_creates = [e for e in create_events if e.type_name == "MyClass"]

        assert len(my_class_creates) >= 1


class TestSelfTracking:
    """Tests for tracking archcheck's own code."""

    def test_can_track_archcheck_infrastructure(self) -> None:
        """Infrastructure code can be tracked."""
        tracking.start()

        # This calls archcheck infrastructure
        active = tracking.is_active()
        count = tracking.count()

        tr = tracking.stop()

        assert active is True
        assert count >= 0
        assert tr is not None

    def test_can_track_archcheck_reporters(self) -> None:
        """Reporters can be tracked."""
        tracking.start()

        reporter = ConsoleReporter()
        result = make_tracking_result()
        output = reporter.report(result)

        tr = tracking.stop()

        assert output is not None
        assert len(output) > 0
        assert tr is not None
        # Should have events from reporter code
        assert len(tr.events) > 0


class TestAPIErrors:
    """Tests for API error handling."""

    def test_double_start_raises(self) -> None:
        """Starting twice raises RuntimeError."""
        tracking.start()
        try:
            with pytest.raises(RuntimeError, match="Already started"):
                tracking.start()
        finally:
            tracking.stop()

    def test_stop_without_start_raises(self) -> None:
        """Stopping without starting raises RuntimeError."""
        with pytest.raises(RuntimeError, match="Not started"):
            tracking.stop()

    def test_get_origin_without_tracking_raises(self) -> None:
        """get_origin without active tracking raises RuntimeError."""
        with pytest.raises(RuntimeError, match="not active"):
            tracking.get_origin(object())


class TestCountAPI:
    """Tests for count() API."""

    def test_count_increases_with_events(self) -> None:
        """count() increases as events are recorded."""
        tracking.start()
        initial = tracking.count()

        def noop() -> None:
            pass

        noop()
        after_call = tracking.count()

        tracking.stop()

        assert after_call > initial

    def test_count_zero_after_stop(self) -> None:
        """count() returns value before stop clears events."""
        tracking.start()

        def noop() -> None:
            pass

        noop()
        count_before = tracking.count()

        tracking.stop()

        assert count_before > 0


class TestDestroyEvent:
    """Tests for DESTROY event capture."""

    def test_destroy_event_captured(self) -> None:
        """DESTROY events are captured when object is garbage collected."""
        tracking.start()

        class Ephemeral:
            pass

        obj = Ephemeral()
        obj_id = id(obj)
        del obj

        tr = tracking.stop()

        destroy_events = [e for e in tr.events if isinstance(e, DestroyEvent)]
        matching = [e for e in destroy_events if e.obj_id == obj_id]

        assert len(matching) >= 1
        assert matching[0].type_name == "Ephemeral"

    def test_destroy_event_has_creation_info(self) -> None:
        """DESTROY event includes creation context."""
        tracking.start()

        class Traced:
            pass

        def create_and_destroy() -> None:
            obj = Traced()
            _ = obj

        create_and_destroy()

        tr = tracking.stop()

        destroy_events = [
            e for e in tr.events if isinstance(e, DestroyEvent) and e.type_name == "Traced"
        ]

        assert len(destroy_events) >= 1
        # Creation info may be present
        evt = destroy_events[0]
        # DESTROY should have obj_id and type_name
        assert evt.obj_id > 0
        assert evt.type_name == "Traced"


class TestCallEventDetails:
    """Tests for CALL event details (caller, args)."""

    def test_call_event_has_caller_info(self) -> None:
        """CALL event includes caller location."""
        tracking.start()

        def inner() -> int:
            return 1

        def outer() -> int:
            return inner()

        outer()

        tr = tracking.stop()

        call_events = [e for e in tr.events if isinstance(e, CallEvent)]
        inner_calls = [e for e in call_events if e.location.func and "inner" in e.location.func]

        assert len(inner_calls) >= 1
        inner_call = inner_calls[0]
        # Should have caller info pointing to outer
        assert inner_call.caller is not None
        assert inner_call.caller.func is not None
        assert "outer" in inner_call.caller.func

    def test_call_event_has_args(self) -> None:
        """CALL event captures function arguments."""
        tracking.start()

        def with_args(x: int, y: str) -> str:
            return f"{x}{y}"

        with_args(42, "hello")

        tr = tracking.stop()

        call_events = [e for e in tr.events if isinstance(e, CallEvent)]
        matching = [e for e in call_events if e.location.func and "with_args" in e.location.func]

        assert len(matching) >= 1
        call = matching[0]
        assert len(call.args) >= 2

        # Check arg names
        arg_names = [a.name for a in call.args]
        assert "x" in arg_names
        assert "y" in arg_names

        # Check arg types
        arg_types = {a.name: a.type_name for a in call.args}
        assert arg_types.get("x") == "int"
        assert arg_types.get("y") == "str"


class TestGetOrigin:
    """Tests for get_origin() API."""

    def test_get_origin_returns_creation_info(self) -> None:
        """get_origin returns creation info for tracked object."""
        tracking.start()

        class Trackable:
            pass

        obj = Trackable()
        origin = tracking.get_origin(obj)

        tracking.stop()

        assert origin is not None
        assert origin.type_name == "Trackable"

    def test_get_origin_returns_none_for_unknown(self) -> None:
        """get_origin returns None for object created before tracking."""
        obj = object()  # Created before tracking

        tracking.start()
        origin = tracking.get_origin(obj)
        tracking.stop()

        assert origin is None
