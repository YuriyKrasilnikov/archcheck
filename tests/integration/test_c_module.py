"""Integration tests for C module quality.

Tests:
- Module loads and has expected API
- String ownership survives frame exit
- No memory corruption on edge cases

Note on RED tests:
- GIL slot (Phase 4A): Cannot detect m_slots absence in runtime without free-threaded build
- Ownership (Phase 2A): Already fixed, tests are regression guards
"""

import importlib.util

import pytest

from archcheck import _tracking
from archcheck.domain import CallEvent, ReturnEvent
from archcheck.infrastructure import tracking


class TestModuleAPI:
    """Tests for module definition correctness."""

    def test_module_loads_with_expected_functions(self) -> None:
        """Module has all expected C API functions."""
        assert hasattr(_tracking, "start")
        assert hasattr(_tracking, "stop")
        assert hasattr(_tracking, "is_active")
        assert hasattr(_tracking, "count")
        assert hasattr(_tracking, "get_origin")

    def test_module_spec_valid(self) -> None:
        """Module spec is properly defined."""
        spec = importlib.util.find_spec("archcheck._tracking")
        assert spec is not None
        assert spec.origin is not None
        assert spec.origin.endswith(".so") or spec.origin.endswith(".pyd")

    def test_module_is_extension(self) -> None:
        """Module is a C extension (not pure Python)."""
        spec = _tracking.__spec__
        assert spec is not None
        assert "ExtensionFileLoader" in type(spec.loader).__name__


class TestStringOwnership:
    """Tests that strings survive frame exit (ownership correctness)."""

    def test_call_event_strings_survive_frame_exit(self) -> None:
        """CALL event file/func strings valid after frame returns."""
        tracking.start()

        def inner() -> int:
            return 42

        inner()
        tr = tracking.stop()

        # Find CALL event for inner()
        call_events = [e for e in tr.events if isinstance(e, CallEvent)]
        inner_calls = [e for e in call_events if e.location.func and "inner" in e.location.func]

        assert len(inner_calls) >= 1
        evt = inner_calls[0]

        # Strings must be valid (not garbage)
        assert evt.location.file is not None
        assert "<string>" in evt.location.file or ".py" in evt.location.file
        assert evt.location.func is not None
        assert "inner" in evt.location.func

    def test_return_event_strings_survive_frame_exit(self) -> None:
        """RETURN event file/func strings valid after frame returns."""
        tracking.start()

        def inner() -> str:
            return "hello"

        inner()
        tr = tracking.stop()

        # Find RETURN event for inner()
        return_events = [e for e in tr.events if isinstance(e, ReturnEvent)]
        inner_returns = [e for e in return_events if e.location.func and "inner" in e.location.func]

        assert len(inner_returns) >= 1
        evt = inner_returns[0]

        # Strings must be valid
        assert evt.location.func is not None
        assert "inner" in evt.location.func
        assert evt.return_type == "str"

    def test_nested_calls_strings_survive_realloc(self) -> None:
        """Strings valid after events array realloc from nested calls."""
        tracking.start()

        def level3() -> int:
            return 3

        def level2() -> int:
            return level3() + 2

        def level1() -> int:
            return level2() + 1

        result = level1()
        assert result == 6

        tr = tracking.stop()

        # All level functions should have valid strings
        for level_name in ["level1", "level2", "level3"]:
            calls = [
                e
                for e in tr.events
                if isinstance(e, CallEvent) and e.location.func and level_name in e.location.func
            ]
            assert len(calls) >= 1, f"Missing CALL for {level_name}"
            assert calls[0].location.file is not None

    def test_many_events_strings_survive_multiple_reallocs(self) -> None:
        """Strings valid after multiple reallocs from many events."""
        tracking.start()

        def noop() -> None:
            pass

        # Force multiple reallocs (initial capacity 4096, each call = 2 events)
        for _ in range(3000):
            noop()

        tr = tracking.stop()

        # Should have ~6000 events, verify some strings
        assert len(tr.events) >= 6000

        # Sample events at different positions (before/after reallocs)
        sample_indices = [0, 100, 1000, 3000, 5000]
        for idx in sample_indices:
            if idx >= len(tr.events):
                continue
            evt = tr.events[idx]
            if isinstance(evt, (CallEvent, ReturnEvent)) and evt.location.func is not None:
                assert isinstance(evt.location.func, str)


class TestEdgeCases:
    """Tests for edge cases and potential memory issues."""

    def test_recursive_deep_no_stack_overflow(self) -> None:
        """Deep recursion doesn't overflow C call stack."""
        tracking.start()

        def recurse(n: int) -> int:
            if n <= 0:
                return 0
            return recurse(n - 1) + 1

        # MAX_STACK_DEPTH is 256, test near limit
        result = recurse(200)
        assert result == 200

        tr = tracking.stop()
        assert tr is not None

    def test_exception_during_tracking_no_leak(self) -> None:
        """Exception during tracked code doesn't leak memory."""
        tracking.start()

        def will_raise() -> None:
            msg = "test error"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="test error"):
            will_raise()

        # stop() should still work
        tr = tracking.stop()
        assert tr is not None
        assert len(tr.events) > 0

    def test_empty_tracking_session(self) -> None:
        """Start/stop with no code between returns valid result."""
        tracking.start()
        tr = tracking.stop()

        assert tr is not None
        # May have some events from stop() itself
        assert isinstance(tr.events, tuple)
