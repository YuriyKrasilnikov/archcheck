"""ctypes boundary tests.

Tests for Python/C boundary safety per PHASE01 section 1.5.

Tests:
- String lifetime: copy before callback returns
- Stop blocking behavior
- Exception capture at boundary
"""

from __future__ import annotations

import gc
import threading
from ctypes import pointer
from typing import TYPE_CHECKING

import pytest

from archcheck.domain.exceptions import CallbackError, StopTracking
from archcheck.infrastructure.safe_callback import (
    EVENT_CALL,
    RawCallEvent,
    RawEvent,
    RawEventData,
    SafeCallback,
)

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def make_event() -> Callable[[int], RawEvent]:
    """Factory for creating RawEvent instances."""

    def _make(kind: int = EVENT_CALL) -> RawEvent:
        call = RawCallEvent(
            callee_file=b"test.py",
            callee_line=10,
            callee_func=b"main",
            caller_file=b"caller.py",
            caller_line=5,
            caller_func=b"caller_func",
            thread_id=1,
            coro_id=0,
            timestamp_ns=1000,
        )
        data = RawEventData(call=call)
        return RawEvent(kind=kind, data=data)

    return _make


# =============================================================================
# String Lifetime Tests
# =============================================================================


class TestStringLifetime:
    """Tests for string ownership at Python/C boundary.

    PHASE01 section 1.5 "String Lifetime":
    "INVARIANT: Python copies strings BEFORE callback returns.
                C strings valid ONLY INSIDE callback."
    """

    def test_string_decoded_inside_callback(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """Strings must be decoded (copied) inside callback."""
        copied: dict[str, str] = {}

        def handler(event: RawEvent) -> None:
            call = event.data.call
            # Correct: decode inside callback copies to Python string
            copied["file"] = call.callee_file.decode("utf-8")
            copied["func"] = call.callee_func.decode("utf-8")

        cb = SafeCallback(handler)
        event = make_event()
        cb._dispatch_safe(pointer(event), None)

        # Copies available after callback
        assert copied["file"] == "test.py"
        assert copied["func"] == "main"

    def test_all_string_fields_copyable(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """All string fields can be copied inside callback."""
        copied: dict[str, str | None] = {}

        def handler(event: RawEvent) -> None:
            call = event.data.call
            copied["callee_file"] = call.callee_file.decode("utf-8") if call.callee_file else None
            copied["callee_func"] = call.callee_func.decode("utf-8") if call.callee_func else None
            copied["caller_file"] = call.caller_file.decode("utf-8") if call.caller_file else None
            copied["caller_func"] = call.caller_func.decode("utf-8") if call.caller_func else None

        cb = SafeCallback(handler)
        event = make_event()
        cb._dispatch_safe(pointer(event), None)

        assert copied["callee_file"] == "test.py"
        assert copied["callee_func"] == "main"
        assert copied["caller_file"] == "caller.py"
        assert copied["caller_func"] == "caller_func"

    def test_numeric_fields_accessible(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """Numeric fields (line, thread_id, etc.) accessible in callback."""
        values: dict[str, int] = {}

        def handler(event: RawEvent) -> None:
            call = event.data.call
            values["callee_line"] = call.callee_line
            values["caller_line"] = call.caller_line
            values["thread_id"] = call.thread_id
            values["coro_id"] = call.coro_id
            values["timestamp_ns"] = call.timestamp_ns

        cb = SafeCallback(handler)
        event = make_event()
        cb._dispatch_safe(pointer(event), None)

        assert values["callee_line"] == 10
        assert values["caller_line"] == 5
        assert values["thread_id"] == 1
        assert values["coro_id"] == 0
        assert values["timestamp_ns"] == 1000


# =============================================================================
# Exception Boundary Tests
# =============================================================================


class TestExceptionBoundary:
    """Tests for exception handling at Python/C boundary.

    PHASE01 section 1.5 "SafeCallback":
    "NEVER re-raises → C continues normally"
    """

    def test_exception_absorbed_not_propagated(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """Exception in handler absorbed, not propagated to C."""

        def handler(_event: RawEvent) -> None:
            raise ValueError("test error")

        cb = SafeCallback(handler)
        event = make_event()

        # Should NOT raise - absorbed
        cb._dispatch_safe(pointer(event), None)

        # But error is pending
        assert cb.has_pending_error

    def test_multiple_exceptions_first_kept(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """First exception preserved, subsequent ignored."""
        count = 0

        def handler(_event: RawEvent) -> None:
            nonlocal count
            count += 1
            raise ValueError(f"error_{count}")

        cb = SafeCallback(handler)
        event = make_event()

        # Three calls, three exceptions
        cb._dispatch_safe(pointer(event), None)
        cb._dispatch_safe(pointer(event), None)
        cb._dispatch_safe(pointer(event), None)

        # Only first kept
        with pytest.raises(CallbackError) as exc_info:
            cb.check_pending_error()

        assert "error_1" in str(exc_info.value.original)

    def test_stop_tracking_sets_flag_not_error(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """StopTracking sets flag, not treated as error."""

        def handler(_event: RawEvent) -> None:
            raise StopTracking

        cb = SafeCallback(handler)
        event = make_event()

        cb._dispatch_safe(pointer(event), None)

        assert cb.stop_requested
        assert not cb.has_pending_error
        cb.check_pending_error()  # Should not raise

    def test_keyboard_interrupt_preserved(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """KeyboardInterrupt re-raised without wrapping."""

        def handler(_event: RawEvent) -> None:
            raise KeyboardInterrupt

        cb = SafeCallback(handler)
        event = make_event()

        cb._dispatch_safe(pointer(event), None)

        with pytest.raises(KeyboardInterrupt):
            cb.check_pending_error()

    def test_system_exit_preserved(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """SystemExit re-raised without wrapping."""

        def handler(_event: RawEvent) -> None:
            raise SystemExit(42)

        cb = SafeCallback(handler)
        event = make_event()

        cb._dispatch_safe(pointer(event), None)

        with pytest.raises(SystemExit) as exc_info:
            cb.check_pending_error()

        assert exc_info.value.code == 42


# =============================================================================
# Concurrent Safety Tests
# =============================================================================


class TestConcurrentSafety:
    """Tests for thread safety at boundary."""

    def test_concurrent_dispatch_thread_safe(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """Multiple threads dispatching is thread-safe."""
        count = 0
        lock = threading.Lock()

        def handler(_event: RawEvent) -> None:
            nonlocal count
            with lock:
                count += 1

        cb = SafeCallback(handler)
        event = make_event()

        def worker() -> None:
            for _ in range(100):
                cb._dispatch_safe(pointer(event), None)

        threads = [threading.Thread(target=worker) for _ in range(8)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert count == 800

    def test_exception_capture_thread_safe(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """Exception capture is thread-safe (first wins)."""
        counter = 0
        lock = threading.Lock()

        def handler(_event: RawEvent) -> None:
            nonlocal counter
            with lock:
                counter += 1
                current = counter
            raise ValueError(f"error_{current}")

        cb = SafeCallback(handler)
        event = make_event()

        threads = [
            threading.Thread(target=lambda: cb._dispatch_safe(pointer(event), None))
            for _ in range(10)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Only one error captured (first)
        assert cb.has_pending_error

        with pytest.raises(CallbackError) as exc_info:
            cb.check_pending_error()

        assert "error_1" in str(exc_info.value.original)


# =============================================================================
# GC Prevention Tests
# =============================================================================


class TestGCPrevention:
    """Tests for GC safety of callback reference."""

    def test_callback_survives_gc(
        self,
        make_event: Callable[[int], RawEvent],
    ) -> None:
        """Callback reference survives garbage collection."""
        called = False

        def handler(_event: RawEvent) -> None:
            nonlocal called
            called = True

        cb = SafeCallback(handler)
        c_callback = cb.c_callback

        # Force GC
        gc.collect()

        # Callback should still work
        event = make_event()
        cb._dispatch_safe(pointer(event), None)

        assert called
        assert cb.c_callback is c_callback

    def test_callback_ref_attribute_exists(self) -> None:
        """_callback_ref attribute prevents GC."""
        cb = SafeCallback(lambda _: None)

        # Internal reference should exist
        assert hasattr(cb, "_callback_ref")
        assert cb._callback_ref is not None


# =============================================================================
# Handler Validation Tests
# =============================================================================


class TestHandlerValidation:
    """Tests for handler validation (FAIL-FIRST)."""

    def test_handler_must_be_callable(self) -> None:
        """Handler must be callable."""
        # String is not callable
        with pytest.raises((TypeError, ValueError)):
            SafeCallback("not callable")  # type: ignore[arg-type]

    def test_none_handler_raises(self) -> None:
        """None handler raises error."""
        with pytest.raises((TypeError, ValueError)):
            SafeCallback(None)  # type: ignore[arg-type]
