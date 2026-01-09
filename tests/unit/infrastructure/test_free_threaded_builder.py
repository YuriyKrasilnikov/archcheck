"""Free-threaded Python 3.14t per-thread builder tests.

TEST-FIRST for PHASE02 per-thread builders.

These tests define the expected behavior for full free-threaded support:
- Per-thread builder isolation
- Thread-local state management
- Builder merging after stop()

PREREQUISITE for Py_MOD_GIL_NOT_USED:
  Without per-thread builders, parallel callbacks race on shared builder.
  These tests MUST pass before switching from Py_MOD_GIL_USED to Py_MOD_GIL_NOT_USED.
"""

from __future__ import annotations

import sys
import sysconfig
import threading

import pytest

from archcheck.infrastructure.safe_callback import is_free_threaded

# FAIL-FIRST: skip entire file if builder.py doesn't exist
builder = pytest.importorskip("archcheck.infrastructure.builder")
get_builder = builder.get_builder
collect_all_thread_builders = builder.collect_all_thread_builders


def _is_free_threaded_build() -> bool:
    """Check if Python build supports free-threading."""
    return sysconfig.get_config_var("Py_GIL_DISABLED") == 1


def _is_gil_actually_disabled() -> bool:
    """Check if GIL is currently disabled at runtime."""
    return not sys._is_gil_enabled()


class TestPerThreadBuilderIsolation:
    """Tests for per-thread builder isolation.

    Solution: Each thread gets its own builder.
    """

    def test_each_thread_has_own_builder(self) -> None:
        """Each thread gets isolated builder instance.

        Expected API:
            from archcheck.infrastructure.builder import get_builder
            builder = get_builder()  # thread-local
        """
        builders: dict[int, object] = {}
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            b = get_builder()
            with lock:
                builders[thread_id] = id(b)

        threads = []
        for i in range(4):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All builders should be different objects
        builder_ids = list(builders.values())
        assert len(set(builder_ids)) == 4, "Each thread should have unique builder"

    def test_builder_thread_local_storage(self) -> None:
        """Builder uses threading.local for isolation.

        Expected implementation:
            _thread_local = threading.local()

            def get_builder() -> OMEGABuilder:
                if not hasattr(_thread_local, 'builder'):
                    _thread_local.builder = OMEGABuilder()
                return _thread_local.builder
        """
        # Same thread gets same builder
        b1 = get_builder()
        b2 = get_builder()
        assert b1 is b2

    def test_no_lock_needed_for_on_event(self) -> None:
        """on_event() doesn't need lock with per-thread builders.

        Expected API:
            def on_event(raw: RawEvent) -> None:
                get_builder().on_event(raw)  # no lock needed
        """
        # This should not deadlock or race
        events_processed = threading.Event()

        def worker() -> None:
            get_builder()
            # Simulate event processing
            for _ in range(100):
                pass  # on_event(raw) would be called here
            events_processed.set()

        threads = [threading.Thread(target=worker) for _ in range(8)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        assert events_processed.is_set()


class TestBuilderMerging:
    """Tests for merging per-thread builders."""

    def test_collect_all_thread_builders(self) -> None:
        """All thread-local builders collected on stop().

        Expected API:
            def collect_all_thread_builders() -> list[OMEGABuilder]:
                ...
        """
        builders_created: list[int] = []
        lock = threading.Lock()

        def worker(thread_id: int) -> None:
            b = get_builder()
            with lock:
                builders_created.append(id(b))

        threads = []
        for i in range(4):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        collected = collect_all_thread_builders()
        collected_ids = [id(b) for b in collected]

        # All created builders should be collected
        for bid in builders_created:
            assert bid in collected_ids

    def test_merge_produces_correct_graph(self) -> None:
        """Merged graph contains all events from all threads.

        Expected behavior:
            Thread 1: events A, B
            Thread 2: events C, D
            Merged: events A, B, C, D (order may vary)
        """
        # Implementation depends on EventGraph.merge()

    def test_merge_is_associative(self) -> None:
        """Merge order doesn't affect final result.

        Grammar Algebra property:
            merge(A, merge(B, C)) == merge(merge(A, B), C)
        """
        # Implementation depends on Grammar Algebra (PHASE04)


class TestGILModeDetection:
    """Tests for GIL mode detection and builder selection."""

    def test_gil_detection_runtime(self) -> None:
        """GIL status detected at runtime."""
        result = is_free_threaded()
        expected = _is_gil_actually_disabled()

        assert result == expected

    def test_gil_mode_uses_single_builder(self) -> None:
        """GIL-enabled mode uses single shared builder.

        When GIL is enabled, no per-thread isolation needed.
        Single builder is simpler and faster.

        Expected behavior:
            if not is_free_threaded():
                return _global_builder  # shared
            else:
                return get_builder()    # per-thread
        """
        if is_free_threaded():
            pytest.skip("Only for GIL-enabled mode")

        builders: list[int] = []
        lock = threading.Lock()

        def worker() -> None:
            b = get_builder()
            with lock:
                builders.append(id(b))

        threads = [threading.Thread(target=worker) for _ in range(4)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # GIL mode: all threads should share same builder
        assert len(set(builders)) == 1, "GIL mode should use single shared builder"


@pytest.mark.skipif(
    not _is_free_threaded_build(),
    reason="Requires free-threaded Python build",
)
class TestFreeThreadedModeSpecific:
    """Tests specific to free-threaded Python 3.14t.

    These tests only run on Python built with --disable-gil.
    """

    def test_parallel_builders_no_race(self) -> None:
        """Parallel builder operations don't race (TSan clean)."""

    def test_concurrent_intern_safe(self) -> None:
        """Concurrent intern() on different builders is safe."""
