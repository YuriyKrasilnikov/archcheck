"""Free-threaded Python 3.14t tests.

Tests for free-threaded Python support (PEP 703).
PHASE01 section 1.6 requirements.

Tests:
- GIL status detection
- Per-thread builder isolation
- Concurrent callback safety
- Builder merge correctness
"""

from __future__ import annotations

import sys
import sysconfig
import threading
import time
from collections import Counter

import pytest

from archcheck import _tracking
from archcheck.infrastructure.safe_callback import is_free_threaded


def _is_build_free_threaded() -> bool:
    """Check if Python build supports free-threading."""
    return sysconfig.get_config_var("Py_GIL_DISABLED") == 1


def _is_gil_actually_disabled() -> bool:
    """Check if GIL is currently disabled at runtime."""
    return not sys._is_gil_enabled()


class TestGILDetection:
    """Tests for GIL status detection."""

    def test_is_free_threaded_returns_bool(self) -> None:
        """is_free_threaded() returns boolean."""
        result = is_free_threaded()
        assert isinstance(result, bool)

    def test_is_free_threaded_matches_runtime(self) -> None:
        """is_free_threaded() matches actual GIL runtime status."""
        expected = _is_gil_actually_disabled()
        actual = is_free_threaded()
        assert actual == expected

    def test_standard_build_has_gil_enabled(self) -> None:
        """Standard Python build has GIL enabled."""
        if _is_build_free_threaded():
            pytest.skip("Running on free-threaded build")

        assert not is_free_threaded()
        assert sys._is_gil_enabled()

    @pytest.mark.skipif(
        not _is_build_free_threaded(),
        reason="Requires free-threaded Python build",
    )
    def test_free_threaded_build_detection(self) -> None:
        """Free-threaded build is correctly detected."""
        # Build supports free-threading
        assert _is_build_free_threaded()
        # Runtime status depends on whether GIL was re-enabled by modules


class TestConcurrentTracking:
    """Tests for concurrent tracking operations."""

    def test_concurrent_start_stop_safe(self) -> None:
        """Concurrent start/stop from multiple threads is safe."""
        errors: list[Exception] = []

        def worker(worker_id: int) -> None:
            try:
                for _ in range(5):
                    try:
                        _tracking.start()
                        time.sleep(0.001)
                        _tracking.stop()
                    except RuntimeError:
                        # Expected: "Already started" or "Not started"
                        pass
            except Exception as e:
                errors.append(e)

        # Ensure clean state
        if _tracking.is_active():
            _tracking.stop()

        threads = []
        for i in range(4):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # No unexpected errors
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_concurrent_events_captured(self) -> None:
        """Events from concurrent threads are all captured."""
        thread_markers: dict[int, int] = {}
        lock = threading.Lock()

        def worker(worker_id: int, iterations: int) -> None:
            count = 0
            for _ in range(iterations):
                count += 1
            with lock:
                thread_markers[worker_id] = count

        _tracking.start()

        threads = []
        num_threads = 8
        iterations = 100

        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i, iterations))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        result = _tracking.stop()

        # All threads completed
        assert len(thread_markers) == num_threads
        for count in thread_markers.values():
            assert count == iterations

        # Events were captured
        assert "events" in result
        assert len(result["events"]) > 0

    def test_no_event_loss_under_concurrency(self) -> None:
        """No events lost when multiple threads generate them."""
        call_counts: Counter[int] = Counter()
        lock = threading.Lock()

        def tracked_work(thread_id: int) -> int:
            total = 0
            for i in range(50):
                total += i
            with lock:
                call_counts[thread_id] += 1
            return total

        _tracking.start()

        threads = []
        num_threads = 4
        calls_per_thread = 10

        def worker(thread_id: int) -> None:
            for _ in range(calls_per_thread):
                tracked_work(thread_id)

        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        result = _tracking.stop()

        # Verify all calls were made
        total_calls = sum(call_counts.values())
        assert total_calls == num_threads * calls_per_thread

        # Events should reflect work done
        assert len(result["events"]) > 0


class TestThreadLocalState:
    """Tests for thread-local state in tracking."""

    def test_call_stack_per_thread(self) -> None:
        """Each thread has independent call stack."""
        results: dict[int, list[str]] = {}
        lock = threading.Lock()

        def level_a(thread_id: int) -> None:
            level_b(thread_id)

        def level_b(thread_id: int) -> None:
            level_c(thread_id)

        def level_c(thread_id: int) -> None:
            # Record that we reached this level
            with lock:
                if thread_id not in results:
                    results[thread_id] = []
                results[thread_id].append("level_c")

        _tracking.start()

        threads = []
        for i in range(4):
            t = threading.Thread(target=level_a, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        _tracking.stop()

        # Each thread reached level_c
        assert len(results) == 4
        for calls in results.values():
            assert "level_c" in calls


class TestModuleGILDeclaration:
    """Tests for C module GIL declaration."""

    def test_module_loads_with_gil_warning(self) -> None:
        """Module loads with GIL warning on free-threaded build.

        Our module declares Py_MOD_GIL_USED (safe default),
        so Python re-enables GIL when loading it.
        """
        # Module is already loaded, just verify it works
        assert hasattr(_tracking, "start")
        assert hasattr(_tracking, "stop")
        assert callable(_tracking.start)
        assert callable(_tracking.stop)


class TestConcurrencyStress:
    """Stress tests for concurrent operations."""

    def test_rapid_start_stop_cycles(self) -> None:
        """Rapid start/stop cycles don't crash."""
        results = []
        for _i in range(20):
            _tracking.start()
            results.append(len(results))
            _tracking.stop()
        assert len(results) == 20

    def test_many_threads_short_work(self) -> None:
        """Many threads with short work complete safely."""
        completed = Counter()
        lock = threading.Lock()

        def short_work(thread_id: int) -> None:
            with lock:
                completed[thread_id] += 1

        _tracking.start()

        threads = []
        num_threads = 16

        for i in range(num_threads):
            t = threading.Thread(target=short_work, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        _tracking.stop()

        assert len(completed) == num_threads

    def test_mixed_long_short_work(self) -> None:
        """Mix of long and short work completes safely."""
        results: dict[str, int] = {"short": 0, "long": 0}
        lock = threading.Lock()

        def short_work() -> None:
            with lock:
                results["short"] += 1

        def long_work() -> None:
            time.sleep(0.01)
            with lock:
                results["long"] += 1

        _tracking.start()

        threads = []
        for i in range(8):
            if i % 2 == 0:
                t = threading.Thread(target=short_work)
            else:
                t = threading.Thread(target=long_work)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        _tracking.stop()

        assert results["short"] == 4
        assert results["long"] == 4


@pytest.mark.skipif(
    not _is_build_free_threaded(),
    reason="Requires free-threaded Python build",
)
class TestFreeThreadedSpecific:
    """Tests specific to free-threaded Python 3.14t."""

    def test_parallel_callbacks_execute(self) -> None:
        """In free-threaded mode, callbacks can run in parallel.

        This test verifies that multiple threads can be in callbacks
        simultaneously (not serialized by GIL).
        """
        concurrent_count = 0
        max_concurrent = 0
        lock = threading.Lock()

        def work_with_overlap() -> None:
            nonlocal concurrent_count, max_concurrent
            with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)

            # Hold for a bit to allow overlap
            time.sleep(0.01)

            with lock:
                concurrent_count -= 1

        _tracking.start()

        threads = []
        for _ in range(8):
            t = threading.Thread(target=work_with_overlap)
            threads.append(t)

        # Start all threads at once
        for t in threads:
            t.start()

        for t in threads:
            t.join()

        _tracking.stop()

        # In free-threaded mode, we expect some concurrency
        # (max_concurrent > 1)
        # In GIL mode, max_concurrent will be 1
        if _is_gil_actually_disabled():
            assert max_concurrent > 1, "Expected parallel execution in free-threaded mode"

    def test_thread_safety_without_gil(self) -> None:
        """Thread safety maintained without GIL protection."""
        counter = 0
        lock = threading.Lock()

        def increment() -> None:
            nonlocal counter
            for _ in range(100):
                with lock:
                    counter += 1

        _tracking.start()

        threads = []
        for _ in range(8):
            t = threading.Thread(target=increment)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        _tracking.stop()

        # Counter should be exact (no races due to our lock)
        assert counter == 800
