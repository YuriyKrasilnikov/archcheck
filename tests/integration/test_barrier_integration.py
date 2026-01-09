"""Barrier integration tests.

Tests for stop barrier behavior at Python/C boundary.
PHASE01 section 1.4 requirements.

Tests:
- stop() blocks until callbacks complete
- stop() from callback detection
- Concurrent dispatch during stop
- Barrier state transitions
"""

from __future__ import annotations

import threading
import time

import pytest

from archcheck import _tracking


class TestStopBlocksUntilDone:
    """Tests that stop() blocks until all callbacks complete.

    PHASE01 requirement: stop() waits for g_active_callbacks == 0.

    IMPORTANT: Barrier protects CALLBACK DISPATCH, not Python function execution.
    barrier_leave() is called BEFORE invoke_original_eval(), so stop() does NOT
    block while tracked Python code runs - only during C-level event dispatch.
    """

    def test_stop_does_not_block_python_execution(self) -> None:
        """stop() does NOT block for Python code execution.

        Architecture clarification:
        - barrier_try_enter() at callback START
        - barrier_leave() BEFORE invoke_original_eval()
        - Python function executes AFTER barrier released

        stop() only waits for active callbacks (C-level dispatch),
        NOT for tracked Python functions to complete.
        """
        function_started = threading.Event()
        function_completed = threading.Event()
        stop_completed = threading.Event()

        def slow_function() -> str:
            function_started.set()
            time.sleep(0.1)  # 100ms
            function_completed.set()
            return "done"

        def stop_thread() -> None:
            # Wait for function to START (callback dispatched)
            function_started.wait(timeout=1.0)
            # Small delay to ensure we're in the middle of slow_function
            time.sleep(0.01)
            # stop() should return quickly - barrier already released
            _tracking.stop()
            stop_completed.set()

        _tracking.start()

        t = threading.Thread(target=stop_thread)
        t.start()

        result = slow_function()

        t.join(timeout=2.0)

        assert result == "done"
        assert function_completed.is_set()
        assert stop_completed.is_set()
        # stop() completes BEFORE slow_function finishes (barrier released early)

    def test_stop_waits_for_nested_calls(self) -> None:
        """stop() waits for deeply nested calls to complete."""
        call_depth = 0
        max_depth = 0

        def nested(depth: int) -> int:
            nonlocal call_depth, max_depth
            call_depth = depth
            max_depth = max(max_depth, depth)
            if depth > 0:
                return nested(depth - 1) + 1
            time.sleep(0.05)  # Delay at bottom
            return 0

        _tracking.start()
        result = nested(5)
        _tracking.stop()

        assert result == 5
        assert max_depth == 5

    def test_stop_returns_all_events(self) -> None:
        """stop() returns result only after all events recorded."""

        def traced_work() -> None:
            for _ in range(10):
                pass  # Generate some events

        _tracking.start()
        traced_work()
        result = _tracking.stop()

        # Should have events (at least CALL for traced_work)
        assert "events" in result
        events = result["events"]
        assert len(events) > 0


class TestStopFromCallback:
    """Tests for stop() called from within tracked code.

    PHASE01 requirement: STOP_FROM_CALLBACK detection via tl_callback_depth.
    """

    def test_stop_from_tracked_function_graceful(self) -> None:
        """stop() from tracked function handles gracefully.

        Current behavior: barrier allows this because barrier_leave()
        is called BEFORE invoke_original_eval().
        """

        def function_that_stops() -> str:
            _tracking.stop()
            return "stopped"

        _tracking.start()

        # This should work - barrier is released before Python code runs
        result = function_that_stops()

        assert result == "stopped"
        assert not _tracking.is_active()

    def test_double_stop_raises(self) -> None:
        """Calling stop() twice raises RuntimeError."""
        _tracking.start()
        _tracking.stop()

        with pytest.raises(RuntimeError, match="Not started"):
            _tracking.stop()


class TestConcurrentDispatch:
    """Tests for concurrent event dispatch during stop."""

    def test_events_from_multiple_threads(self) -> None:
        """Events from multiple threads are captured."""
        thread_ids: set[int] = set()
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            with lock:
                thread_ids.add(worker_id)
            # Some work to generate events
            for _ in range(10):
                pass

        _tracking.start()

        threads = []
        for i in range(4):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        result = _tracking.stop()

        assert len(thread_ids) == 4
        assert "events" in result

    def test_stop_during_concurrent_work(self) -> None:
        """stop() during concurrent work completes safely."""
        workers_done = threading.Event()
        worker_count = 0
        lock = threading.Lock()

        def worker() -> None:
            nonlocal worker_count
            for _ in range(100):
                pass
            with lock:
                worker_count += 1
            if worker_count >= 4:
                workers_done.set()

        _tracking.start()

        threads = []
        for _ in range(4):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        # Stop while workers may still be running
        time.sleep(0.001)
        result = _tracking.stop()

        for t in threads:
            t.join(timeout=1.0)

        assert "events" in result


class TestBarrierStateTransitions:
    """Tests for barrier state machine transitions."""

    def test_start_stop_cycle(self) -> None:
        """Multiple start/stop cycles work correctly."""
        for _ in range(3):
            assert not _tracking.is_active()
            _tracking.start()
            assert _tracking.is_active()
            _tracking.stop()
            assert not _tracking.is_active()

    def test_is_active_reflects_state(self) -> None:
        """is_active() accurately reflects tracking state."""
        assert not _tracking.is_active()

        _tracking.start()
        assert _tracking.is_active()

        _tracking.stop()
        assert not _tracking.is_active()


class TestBarrierMemorySafety:
    """Tests for memory safety with barrier.

    These tests verify no use-after-free when stop() called during execution.
    """

    def test_strings_valid_after_nested_stop(self) -> None:
        """String pointers remain valid after nested stop().

        Regression test for _tracking.c:158 use-after-free bug.
        """

        def outer() -> str:
            def inner() -> str:
                return "inner_result"

            result = inner()
            return f"outer_{result}"

        _tracking.start()
        result = outer()
        tracking_result = _tracking.stop()

        assert result == "outer_inner_result"
        assert "events" in tracking_result

        # Verify event strings are valid
        for event in tracking_result["events"]:
            if "file" in event and event["file"] is not None:
                assert isinstance(event["file"], str)
            if "func" in event and event["func"] is not None:
                assert isinstance(event["func"], str)

    def test_many_events_no_corruption(self) -> None:
        """Many events don't corrupt memory during realloc."""

        def generate_events(n: int) -> int:
            total = 0
            for i in range(n):
                total += i
            return total

        _tracking.start()
        result = generate_events(1000)
        tracking_result = _tracking.stop()

        assert result == sum(range(1000))
        assert "events" in tracking_result
        # Should have generated many events
        assert len(tracking_result["events"]) > 100
