"""Tests for SafeCallback.

Tests exception capture, StopTracking handling, and thread safety.
"""

from __future__ import annotations

import gc
import sys
import sysconfig
import threading
from collections import Counter
from ctypes import pointer
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from archcheck.domain.exceptions import CallbackError, StopTracking
from archcheck.infrastructure.safe_callback import (
    EVENT_CALL,
    RawCallEvent,
    RawEvent,
    RawEventData,
    SafeCallback,
    decode_c_string,
    is_free_threaded,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _noop_handler(_event: RawEvent) -> None:
    """No-op handler for tests that don't need event processing."""


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def make_event() -> Callable[[int], RawEvent]:
    """Factory for creating RawEvent instances."""

    def _make(kind: int = EVENT_CALL) -> RawEvent:
        call = RawCallEvent(
            callee_file=b"test.py",
            callee_line=10,
            callee_func=b"main",
            caller_file=None,
            caller_line=0,
            caller_func=None,
            thread_id=1,
            coro_id=0,
            timestamp_ns=1000,
        )
        data = RawEventData(call=call)
        return RawEvent(kind=kind, data=data)

    return _make


# =============================================================================
# Basic Tests
# =============================================================================


class TestSafeCallbackBasic:
    """Basic SafeCallback functionality."""

    def test_handler_called(self, make_event: Callable[[int], RawEvent]) -> None:
        """Handler receives events."""
        received: list[RawEvent] = []

        def handler(event: RawEvent) -> None:
            received.append(event)

        cb = SafeCallback(handler)
        event = make_event()

        # Simulate C calling the callback
        cb._dispatch_safe(pointer(event), None)

        assert len(received) == 1
        assert received[0].kind == EVENT_CALL

    def test_c_callback_property(self) -> None:
        """c_callback returns CFUNCTYPE instance."""
        cb = SafeCallback(_noop_handler)
        c_cb = cb.c_callback

        # Should be a ctypes function pointer (callable)
        assert c_cb is not None
        assert callable(c_cb)
        assert "CFunctionType" in type(c_cb).__name__

    def test_no_pending_error_initially(self) -> None:
        """No error pending after init."""
        cb = SafeCallback(_noop_handler)

        assert not cb.has_pending_error
        cb.check_pending_error()  # Should not raise

    def test_no_stop_requested_initially(self) -> None:
        """Stop not requested after init."""
        cb = SafeCallback(_noop_handler)

        assert not cb.stop_requested


# =============================================================================
# Exception Handling Tests
# =============================================================================


class TestExceptionCapture:
    """Exception capture behavior."""

    def test_exception_captured(self, make_event: Callable[[int], RawEvent]) -> None:
        """Handler exception captured, not re-raised."""

        def handler(_event: RawEvent) -> None:
            raise ValueError("test error")

        cb = SafeCallback(handler)
        event = make_event()

        # Should NOT raise (absorbed)
        cb._dispatch_safe(pointer(event), None)

        # But error is pending
        assert cb.has_pending_error

        with pytest.raises(CallbackError) as exc_info:
            cb.check_pending_error()

        assert isinstance(exc_info.value.original, ValueError)
        assert "test error" in str(exc_info.value)

    def test_first_exception_preserved(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """Only first exception kept, subsequent ignored."""
        call_count = 0

        def handler(_event: RawEvent) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first")
            raise RuntimeError("second")

        cb = SafeCallback(handler)
        event = make_event()

        # Two calls
        cb._dispatch_safe(pointer(event), None)
        cb._dispatch_safe(pointer(event), None)

        # First exception preserved
        with pytest.raises(CallbackError) as exc_info:
            cb.check_pending_error()

        assert isinstance(exc_info.value.original, ValueError)
        assert "first" in str(exc_info.value.original)

    def test_check_pending_error_idempotent(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """check_pending_error() can be called multiple times."""

        def handler(_event: RawEvent) -> None:
            raise ValueError("test")

        cb = SafeCallback(handler)
        event = make_event()
        cb._dispatch_safe(pointer(event), None)

        # Multiple calls raise same error
        with pytest.raises(CallbackError):
            cb.check_pending_error()

        with pytest.raises(CallbackError):
            cb.check_pending_error()


# =============================================================================
# StopTracking Tests
# =============================================================================


class TestStopTracking:
    """StopTracking exception handling."""

    def test_stop_tracking_sets_flag(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """StopTracking sets stop_requested, not error."""

        def handler(_event: RawEvent) -> None:
            raise StopTracking

        cb = SafeCallback(handler)
        event = make_event()

        cb._dispatch_safe(pointer(event), None)

        assert cb.stop_requested
        assert not cb.has_pending_error  # Not an error
        cb.check_pending_error()  # Should not raise

    def test_stop_tracking_before_error(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """StopTracking then error: both captured."""
        call_count = 0

        def handler(_event: RawEvent) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise StopTracking
            raise ValueError("after stop")

        cb = SafeCallback(handler)
        event = make_event()

        cb._dispatch_safe(pointer(event), None)  # StopTracking
        cb._dispatch_safe(pointer(event), None)  # ValueError

        assert cb.stop_requested
        assert cb.has_pending_error

        with pytest.raises(CallbackError) as exc_info:
            cb.check_pending_error()

        assert isinstance(exc_info.value.original, ValueError)


# =============================================================================
# Reset Tests
# =============================================================================


class TestReset:
    """SafeCallback reset functionality."""

    def test_reset_clears_error(self, make_event: Callable[[int], RawEvent]) -> None:
        """reset() clears pending error."""

        def handler(_event: RawEvent) -> None:
            raise ValueError("test")

        cb = SafeCallback(handler)
        event = make_event()
        cb._dispatch_safe(pointer(event), None)

        assert cb.has_pending_error

        cb.reset()

        assert not cb.has_pending_error
        cb.check_pending_error()  # Should not raise

    def test_reset_clears_stop_requested(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """reset() clears stop_requested."""

        def handler(_event: RawEvent) -> None:
            raise StopTracking

        cb = SafeCallback(handler)
        event = make_event()
        cb._dispatch_safe(pointer(event), None)

        assert cb.stop_requested

        cb.reset()

        assert not cb.stop_requested


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Thread safety for free-threaded Python 3.14."""

    def test_concurrent_dispatch(self, make_event: Callable[[int], RawEvent]) -> None:
        """Multiple threads can dispatch concurrently."""
        call_count = 0
        lock = threading.Lock()

        def handler(_event: RawEvent) -> None:
            nonlocal call_count
            with lock:
                call_count += 1

        cb = SafeCallback(handler)
        event = make_event()

        threads: list[threading.Thread] = []
        for _ in range(10):

            def worker() -> None:
                for _ in range(100):
                    cb._dispatch_safe(pointer(event), None)

            t = threading.Thread(target=worker)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert call_count == 1000

    def test_concurrent_exception_capture(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """First exception captured even with concurrent errors."""

        def handler(_event: RawEvent) -> None:
            raise ValueError("concurrent error")

        cb = SafeCallback(handler)
        event = make_event()

        threads: list[threading.Thread] = []
        for _ in range(10):

            def worker() -> None:
                cb._dispatch_safe(pointer(event), None)

            t = threading.Thread(target=worker)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Only one error captured (first)
        assert cb.has_pending_error

        with pytest.raises(CallbackError) as exc_info:
            cb.check_pending_error()

        assert isinstance(exc_info.value.original, ValueError)


# =============================================================================
# Utility Tests
# =============================================================================


class TestUtilities:
    """Utility function tests."""

    def test_decode_c_string_bytes(self) -> None:
        """decode_c_string handles bytes."""
        result = decode_c_string(b"hello")
        assert result == "hello"

    def test_decode_c_string_none(self) -> None:
        """decode_c_string handles None."""
        result = decode_c_string(None)
        assert result is None

    def test_decode_c_string_utf8(self) -> None:
        """decode_c_string handles UTF-8."""
        result = decode_c_string("héllo".encode())
        assert result == "héllo"

    def test_is_free_threaded(self) -> None:
        """is_free_threaded returns bool."""
        result = is_free_threaded()
        assert isinstance(result, bool)
        # Can't assert value - depends on Python build


# =============================================================================
# GC Prevention Tests
# =============================================================================


class TestGCPrevention:
    """Ensure callback not garbage collected."""

    def test_callback_ref_prevents_gc(self) -> None:
        """_callback_ref keeps callback alive."""
        handler = MagicMock()
        cb = SafeCallback(handler)

        # Get weak reference to handler
        c_callback = cb.c_callback

        # Force GC
        gc.collect()

        # Callback should still be valid
        assert cb.c_callback is c_callback
        assert cb._callback_ref is not None


# =============================================================================
# String Copy Tests
# =============================================================================


class TestStringCopy:
    """String ownership: copy in Python before callback returns."""

    def test_string_copy_before_return(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """Strings must be copied in handler, not stored as C pointers.

        C owns the strings in RawEvent. They are valid ONLY during callback.
        Handler MUST copy (decode) strings before returning.
        This test verifies the pattern works.
        """
        copied_strings: list[str] = []

        def handler(event: RawEvent) -> None:
            # Correct pattern: decode (copy) strings immediately
            call_data = event.data.call
            if call_data.callee_file:
                copied_strings.append(call_data.callee_file.decode("utf-8"))
            if call_data.callee_func:
                copied_strings.append(call_data.callee_func.decode("utf-8"))

        cb = SafeCallback(handler)
        event = make_event(EVENT_CALL)

        cb._dispatch_safe(pointer(event), None)

        # Strings were copied
        assert len(copied_strings) == 2
        assert copied_strings[0] == "test.py"
        assert copied_strings[1] == "main"


# =============================================================================
# Barrier Integration Tests (Stop Behavior)
# =============================================================================


class TestStopBehavior:
    """Tests for stop() and barrier integration."""

    def test_stop_from_callback_detected(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """StopTracking in handler sets stop_requested flag.

        When handler raises StopTracking, SafeCallback captures it
        and sets _stop_requested. This signals caller to stop tracking.
        """

        def handler(_event: RawEvent) -> None:
            raise StopTracking

        cb = SafeCallback(handler)
        event = make_event(EVENT_CALL)

        # Should not raise
        cb._dispatch_safe(pointer(event), None)

        # Flag should be set
        assert cb.stop_requested
        assert not cb.has_pending_error

    def test_keyboard_interrupt_preserved(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """KeyboardInterrupt re-raised in check_pending_error().

        Ctrl+C during callback should not be swallowed.
        It's captured and re-raised after stop().
        """

        def handler(_event: RawEvent) -> None:
            raise KeyboardInterrupt

        cb = SafeCallback(handler)
        event = make_event(EVENT_CALL)

        cb._dispatch_safe(pointer(event), None)

        # Has pending error (KeyboardInterrupt)
        assert cb.has_pending_error

        # Re-raises KeyboardInterrupt directly (not wrapped)
        with pytest.raises(KeyboardInterrupt):
            cb.check_pending_error()

    def test_system_exit_preserved(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """SystemExit re-raised in check_pending_error().

        sys.exit() during callback should not be swallowed.
        """

        def handler(_event: RawEvent) -> None:
            raise SystemExit(42)

        cb = SafeCallback(handler)
        event = make_event(EVENT_CALL)

        cb._dispatch_safe(pointer(event), None)

        with pytest.raises(SystemExit) as exc_info:
            cb.check_pending_error()

        assert exc_info.value.code == 42


# =============================================================================
# Free-Threaded Python Tests
# =============================================================================


class TestFreeThreaded:
    """Tests specific to free-threaded Python 3.14+ (no GIL)."""

    def test_is_free_threaded_matches_build(self) -> None:
        """is_free_threaded() returns correct value for current build.

        Standard build: GIL always enabled, is_free_threaded() = False.
        Free-threaded build: GIL can be re-enabled by modules (Py_MOD_GIL_USED),
        so is_free_threaded() reflects actual runtime status, not build config.
        """
        build_free_threaded = sysconfig.get_config_var("Py_GIL_DISABLED") == 1
        runtime_gil_disabled = not sys._is_gil_enabled()

        result = is_free_threaded()

        # Result must match actual runtime GIL status
        assert result == runtime_gil_disabled

        # In standard build, GIL cannot be disabled at runtime
        if not build_free_threaded:
            assert not runtime_gil_disabled

    def test_concurrent_callbacks_no_race(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """Multiple threads calling callback concurrently - no data race.

        In free-threaded Python, callbacks can run in parallel.
        SafeCallback must be thread-safe.
        """
        call_counts: Counter[int] = Counter()
        lock = threading.Lock()

        def handler(_event: RawEvent) -> None:
            thread_id = threading.get_ident()
            with lock:
                call_counts[thread_id] += 1

        cb = SafeCallback(handler)
        event = make_event(EVENT_CALL)

        threads: list[threading.Thread] = []
        calls_per_thread = 100
        num_threads = 8

        def worker() -> None:
            for _ in range(calls_per_thread):
                cb._dispatch_safe(pointer(event), None)

        for _ in range(num_threads):
            t = threading.Thread(target=worker)
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All calls completed
        total_calls = sum(call_counts.values())
        assert total_calls == num_threads * calls_per_thread

        # Multiple threads participated
        assert len(call_counts) == num_threads

    def test_exception_capture_thread_safe(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """First exception captured even with concurrent errors.

        Multiple threads raising exceptions - only first is kept.
        No race condition on _pending_error.
        """
        error_count = 0
        lock = threading.Lock()

        def handler(_event: RawEvent) -> None:
            nonlocal error_count
            with lock:
                error_count += 1
                current = error_count
            raise ValueError(f"error_{current}")

        cb = SafeCallback(handler)
        event = make_event(EVENT_CALL)

        threads: list[threading.Thread] = []
        for _ in range(10):
            t = threading.Thread(
                target=lambda: cb._dispatch_safe(pointer(event), None),
            )
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one error captured (first one)
        assert cb.has_pending_error

        with pytest.raises(CallbackError) as exc_info:
            cb.check_pending_error()

        # Should be error_1 (first)
        assert "error_1" in str(exc_info.value.original)
