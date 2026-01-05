"""Tracker service: orchestration for C tracking."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from archcheck.domain.exceptions import AlreadyActiveError, NotExitedError
from archcheck.infrastructure import tracking

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from archcheck.domain.events import TrackingResult


@dataclass(frozen=True, slots=True)
class TrackingHandle:
    """Handle to tracking result. Externally immutable, single-write internal.

    Result available after context exit via .result property.
    Raises NotExitedError if accessed before context exit.
    """

    _result_value: TrackingResult | None = None

    @property
    def result(self) -> TrackingResult:
        """Get tracking result. Available only after context exit.

        Raises:
            NotExitedError: Context not exited yet.
        """
        if self._result_value is None:
            raise NotExitedError
        return self._result_value


def _ensure_not_active() -> None:
    """FAIL-FIRST: raise if tracking already active."""
    if tracking.is_active():
        raise AlreadyActiveError


class TrackerService:
    """Orchestrates C tracking: start → run → stop.

    Contracts:
        - FAIL-FIRST: AlreadyActiveError if already tracking
        - Data Completeness: stop() always called (try/finally)
        - Immutability: TrackingResult and TrackingHandle frozen
    """

    def track[T](self, target: Callable[[], T]) -> tuple[T, TrackingResult]:
        """Track callable execution, return result and tracking data.

        Args:
            target: Zero-argument callable to track.

        Returns:
            (target_result, tracking_result)

        Raises:
            AlreadyActiveError: Tracking already active.
        """
        _ensure_not_active()
        tracking.start()
        try:
            result = target()
        finally:
            tracking_result = tracking.stop()
        return result, tracking_result

    @contextmanager
    def track_context(self) -> Iterator[TrackingHandle]:
        """Context manager for tracking code blocks.

        Usage:
            with tracker.track_context() as handle:
                do_work()
            print(handle.result.events)

        Raises:
            AlreadyActiveError: Tracking already active.
        """
        _ensure_not_active()
        handle = TrackingHandle()
        tracking.start()
        try:
            yield handle
        finally:
            object.__setattr__(handle, "_result_value", tracking.stop())
