"""SafeCallback: Exception-absorbing wrapper for C callback dispatch.

Wraps Python callback for safe invocation from C code.
NEVER re-raises into C — captures exceptions for later handling.

WHY CATCH IN PYTHON (not in C):
  When Python raises in ctypes callback, ctypes calls PyErr_FormatUnraisable()
  which CLEARS the exception. By the time control returns to C, PyErr_Occurred()
  is NULL. The ONLY chance to capture the exception is in Python wrapper BEFORE
  ctypes clears it. C code cannot see the error after callback returns.

  Flow:
    C: g_callback(event, user_data)  →  Python: _dispatch_safe()
                                              │
                                         self._handler(event)
                                              │
                                         if raises: CATCH HERE (last chance!)
                                              │
    C: (PyErr_Occurred() == NULL)    ←  return (ctypes cleared error)

Thread-safe for free-threaded Python 3.14 (PEP 703).

Design for Known Future:
  - Ready for callback-based C API (PHASE 2)
  - Integrates with Stop Barrier (STOP_FROM_CALLBACK detection)
  - Per-thread builders pattern supported via thread-local state
"""

from __future__ import annotations

import sys
import threading
from ctypes import CFUNCTYPE, POINTER, Structure, c_char_p, c_int, c_uint64, c_void_p
from typing import TYPE_CHECKING, ClassVar, Protocol

from archcheck.domain.exceptions import CallbackError, InvalidHandlerError, StopTracking

if TYPE_CHECKING:
    from collections.abc import Callable
    from ctypes import _FuncPointer


# =============================================================================
# ctypes Structures (match c/tracking/callback.h)
# =============================================================================


class RawCallEvent(Structure):
    """C RawCallEvent struct."""

    _fields_: ClassVar[list[tuple[str, type]]] = [
        ("callee_file", c_char_p),
        ("callee_line", c_int),
        ("callee_func", c_char_p),
        ("caller_file", c_char_p),
        ("caller_line", c_int),
        ("caller_func", c_char_p),
        ("thread_id", c_uint64),
        ("coro_id", c_uint64),
        ("timestamp_ns", c_uint64),
    ]


class RawReturnEvent(Structure):
    """C RawReturnEvent struct."""

    _fields_: ClassVar[list[tuple[str, type]]] = [
        ("file", c_char_p),
        ("line", c_int),
        ("func", c_char_p),
        ("thread_id", c_uint64),
        ("timestamp_ns", c_uint64),
        ("has_exception", c_int),
    ]


class RawCreateEvent(Structure):
    """C RawCreateEvent struct."""

    _fields_: ClassVar[list[tuple[str, type]]] = [
        ("obj_id", c_uint64),
        ("type_name", c_char_p),
        ("file", c_char_p),
        ("line", c_int),
        ("func", c_char_p),
        ("thread_id", c_uint64),
        ("timestamp_ns", c_uint64),
    ]


class RawDestroyEvent(Structure):
    """C RawDestroyEvent struct."""

    _fields_: ClassVar[list[tuple[str, type]]] = [
        ("obj_id", c_uint64),
        ("type_name", c_char_p),
        ("thread_id", c_uint64),
        ("timestamp_ns", c_uint64),
    ]


class RawEventData(Structure):
    """Union of all event types (simplified as largest)."""

    _fields_: ClassVar[list[tuple[str, type]]] = [
        ("call", RawCallEvent),
    ]


class RawEvent(Structure):
    """C RawEvent struct."""

    _fields_: ClassVar[list[tuple[str, type]]] = [
        ("kind", c_int),
        ("data", RawEventData),
    ]


class RawEventPointer(Protocol):
    """Protocol for ctypes pointer to RawEvent.

    Structural type for POINTER(RawEvent) — enables proper typing
    without relying on private ctypes._Pointer.
    """

    @property
    def contents(self) -> RawEvent:
        """Dereference pointer to get RawEvent struct."""
        ...


# Event kind constants (match c/tracking/callback.h EventKind)
EVENT_CALL = 0
EVENT_RETURN = 1
EVENT_CREATE = 2
EVENT_DESTROY = 3

# Callback type: void (*)(const RawEvent*, void*)
EventCallbackType = CFUNCTYPE(None, POINTER(RawEvent), c_void_p)


# =============================================================================
# Free-threaded Python 3.14 Detection
# =============================================================================


def is_free_threaded() -> bool:
    """Detect if GIL is currently disabled (runtime check).

    Returns True if GIL is disabled in the running process.

    WHY sys._is_gil_enabled() (not sysconfig):
      - sysconfig.get_config_var("Py_GIL_DISABLED") checks BUILD configuration
      - But GIL can be ENABLED at runtime even in free-threaded builds:
        * PYTHON_GIL=1 environment variable
        * -X gil command-line option
        * Incompatible C extension loaded (auto-enables GIL with warning)
      - We need RUNTIME status, not build status
      - sys._is_gil_enabled() is documented in Python 3.14 free-threading docs
        (underscore is historical, not "private" — it's the official API)

    See: https://docs.python.org/3/howto/free-threading-python.html
    """
    # SLF001: sys._is_gil_enabled is documented public API for runtime GIL detection
    return not sys._is_gil_enabled()  # noqa: SLF001


# =============================================================================
# SafeCallback
# =============================================================================


class SafeCallback:
    """Exception-absorbing wrapper for C callback dispatch.

    Contract:
      - _dispatch_safe() NEVER re-raises into C
      - First exception captured in _pending_error
      - StopTracking sets _stop_requested flag
      - check_pending_error() raises after stop()

    Thread Safety (Python 3.14 free-threaded):
      - _lock protects _pending_error and _stop_requested
      - Each callback invocation is atomic w.r.t. error capture

    GC Prevention:
      - _callback_ref prevents garbage collection of ctypes callback
      - C holds raw pointer, would dangle without this reference

    String Lifetime:
      - C strings valid ONLY during callback
      - Handler MUST copy any strings needed after return
    """

    __slots__ = (
        "_callback_ref",
        "_handler",
        "_lock",
        "_pending_error",
        "_stop_requested",
    )

    def __init__(self, handler: Callable[[RawEvent], None]) -> None:
        """Initialize with user handler.

        Args:
            handler: Called for each event. Must copy strings before returning.
                     May raise StopTracking to request stop.
                     Other exceptions captured in _pending_error.

        Raises:
            InvalidHandlerError: If handler is not callable.
        """
        # FAIL-FIRST: validate handler immediately
        if not callable(handler):
            raise InvalidHandlerError(type(handler))

        self._handler = handler
        self._lock = threading.Lock()
        self._pending_error: BaseException | None = None
        self._stop_requested = False

        # CRITICAL: Store reference to prevent GC
        # C holds pointer to this callback, would become dangling without ref
        self._callback_ref: _FuncPointer = EventCallbackType(self._dispatch_safe)

    @property
    def c_callback(self) -> _FuncPointer:
        """Get ctypes callback for passing to C.

        Returns the CFUNCTYPE instance that can be passed to C code.
        """
        return self._callback_ref

    @property
    def stop_requested(self) -> bool:
        """Check if StopTracking was raised by handler."""
        with self._lock:
            return self._stop_requested

    @property
    def has_pending_error(self) -> bool:
        """Check if an error is pending."""
        with self._lock:
            return self._pending_error is not None

    def _dispatch_safe(
        self,
        event_ptr: RawEventPointer,
        user_data: c_void_p,
    ) -> None:
        """Called from C. NEVER re-raises.

        Exception Algebra:
          - Success: handler executes normally
          - StopTracking: sets _stop_requested, no error
          - Other exception: stored in _pending_error (first only)

        Args:
            event_ptr: Pointer to RawEvent. Valid ONLY during this call.
            user_data: Opaque pointer (unused, for C API compatibility).
        """
        del user_data  # Unused

        try:
            # Dereference pointer to get struct
            # Handler MUST copy any strings it needs
            self._handler(event_ptr.contents)

        except StopTracking:
            with self._lock:
                self._stop_requested = True

        # BLE001: We MUST catch all exceptions here — ctypes will clear them otherwise.
        # This is the ONLY place to capture exceptions from handler (see module docstring).
        # KeyboardInterrupt/SystemExit handled separately to re-raise them properly.
        except Exception as exc:  # noqa: BLE001
            # Capture first exception only (idempotent)
            with self._lock:
                if self._pending_error is None:
                    self._pending_error = exc

        except KeyboardInterrupt:
            # Preserve KeyboardInterrupt — will be re-raised in check_pending_error()
            # Cannot propagate through C, so we save and re-raise later
            with self._lock:
                if self._pending_error is None:
                    self._pending_error = KeyboardInterrupt()

        except SystemExit as exc:
            # Preserve SystemExit — will be re-raised in check_pending_error()
            with self._lock:
                if self._pending_error is None:
                    self._pending_error = exc

        # NEVER re-raise — C continues normally

    def check_pending_error(self) -> None:
        """Raise if callback failed. Call AFTER stop().

        Raises:
            KeyboardInterrupt: If callback received Ctrl+C.
            SystemExit: If callback called sys.exit().
            CallbackError: If callback raised other exception.

        Idempotent: Can be called multiple times, raises same error.
        """
        with self._lock:
            if self._pending_error is None:
                return

            # Re-raise system exceptions directly (not wrapped)
            if isinstance(self._pending_error, (KeyboardInterrupt, SystemExit)):
                raise self._pending_error

            # Wrap other exceptions
            raise CallbackError(self._pending_error)

    def reset(self) -> None:
        """Reset state for reuse.

        Clears pending error and stop request.
        Call before starting new tracking session.
        """
        with self._lock:
            self._pending_error = None
            self._stop_requested = False


# =============================================================================
# Convenience: decode C strings
# =============================================================================


def decode_c_string(c_str: c_char_p | None) -> str | None:
    """Decode C string to Python str.

    Args:
        c_str: ctypes c_char_p (bytes or None).

    Returns:
        Decoded string or None if input is None/null.
    """
    if c_str is None:
        return None
    # c_char_p.value is bytes or None
    value = c_str if isinstance(c_str, bytes) else getattr(c_str, "value", None)
    if value is None:
        return None
    return value.decode("utf-8", errors="replace")
