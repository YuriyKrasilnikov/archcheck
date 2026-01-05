"""Tests for TrackerService.

Tests:
- TrackingHandle result access before/after context exit
- TrackerService.track() execution and result
- TrackerService.track_context() context manager
- AlreadyActiveError on double tracking
- try/finally guarantees stop() is called
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from archcheck.application.services.tracker import TrackerService, TrackingHandle
from archcheck.domain.exceptions import AlreadyActiveError, NotExitedError
from tests.factories import make_tracking_result

if TYPE_CHECKING:
    from archcheck.domain.events import TrackingResult


class TestTrackingHandle:
    """Tests for TrackingHandle."""

    def test_result_before_exit_raises_not_exited_error(self) -> None:
        """Accessing result before context exit raises NotExitedError."""
        handle = TrackingHandle()
        with pytest.raises(NotExitedError):
            _ = handle.result

    def test_result_after_set_returns_tracking_result(self) -> None:
        """Result is accessible after being set."""
        handle = TrackingHandle()
        tracking_result = make_tracking_result()
        object.__setattr__(handle, "_result_value", tracking_result)
        assert handle.result is tracking_result

    def test_handle_is_frozen_dataclass(self) -> None:
        """TrackingHandle is frozen (immutable)."""
        handle = TrackingHandle()
        # Direct setattr raises AttributeError on frozen dataclass
        pytest.raises(AttributeError, setattr, handle, "_result_value", None)


class TestTrackerServiceTrack:
    """Tests for TrackerService.track()."""

    @patch("archcheck.application.services.tracker.tracking")
    def test_track_returns_result_and_tracking_data(self, mock_tracking: MagicMock) -> None:
        """track() returns tuple of (target_result, tracking_result)."""
        mock_tracking.is_active.return_value = False
        tracking_result = make_tracking_result()
        mock_tracking.stop.return_value = tracking_result

        service = TrackerService()
        target_result, returned_tracking = service.track(lambda: 42)

        assert target_result == 42
        assert returned_tracking is tracking_result
        mock_tracking.start.assert_called_once()
        mock_tracking.stop.assert_called_once()

    @patch("archcheck.application.services.tracker.tracking")
    def test_track_raises_already_active_error_if_active(self, mock_tracking: MagicMock) -> None:
        """track() raises AlreadyActiveError if tracking is already active."""
        mock_tracking.is_active.return_value = True

        service = TrackerService()
        with pytest.raises(AlreadyActiveError):
            service.track(lambda: None)

        mock_tracking.start.assert_not_called()

    @patch("archcheck.application.services.tracker.tracking")
    def test_track_calls_stop_on_target_exception(self, mock_tracking: MagicMock) -> None:
        """track() calls stop() even when target raises exception."""
        mock_tracking.is_active.return_value = False
        tracking_result = make_tracking_result()
        mock_tracking.stop.return_value = tracking_result

        def failing_target() -> None:
            msg = "target failed"
            raise ValueError(msg)

        service = TrackerService()
        with pytest.raises(ValueError, match="target failed"):
            service.track(failing_target)

        mock_tracking.stop.assert_called_once()


class TestTrackerServiceTrackContext:
    """Tests for TrackerService.track_context()."""

    @patch("archcheck.application.services.tracker.tracking")
    def test_track_context_provides_result_after_exit(self, mock_tracking: MagicMock) -> None:
        """track_context() provides result via handle after context exit."""
        mock_tracking.is_active.return_value = False
        tracking_result = make_tracking_result()
        mock_tracking.stop.return_value = tracking_result

        service = TrackerService()
        with service.track_context() as handle:
            # Result not available during context - should raise
            pytest.raises(NotExitedError, lambda: handle.result)

        assert handle.result is tracking_result

    @patch("archcheck.application.services.tracker.tracking")
    def test_track_context_raises_already_active_error(self, mock_tracking: MagicMock) -> None:
        """track_context() raises AlreadyActiveError if tracking is active."""
        mock_tracking.is_active.return_value = True

        service = TrackerService()
        with pytest.raises(AlreadyActiveError), service.track_context():
            pass

        mock_tracking.start.assert_not_called()

    @patch("archcheck.application.services.tracker.tracking")
    def test_track_context_calls_stop_on_exception(self, mock_tracking: MagicMock) -> None:
        """track_context() calls stop() even when block raises exception."""
        mock_tracking.is_active.return_value = False
        tracking_result = make_tracking_result()
        mock_tracking.stop.return_value = tracking_result

        service = TrackerService()
        handle: TrackingHandle | None = None
        try:
            with service.track_context() as handle:
                msg = "block failed"
                raise ValueError(msg)
        except ValueError:
            pass

        mock_tracking.stop.assert_called_once()
        assert handle is not None
        assert handle.result is tracking_result

    @patch("archcheck.application.services.tracker.tracking")
    def test_track_context_start_stop_order(self, mock_tracking: MagicMock) -> None:
        """track_context() calls start() before body and stop() after."""
        mock_tracking.is_active.return_value = False

        call_order: list[str] = []

        def start_side_effect() -> None:
            call_order.append("start")

        def stop_side_effect() -> TrackingResult:
            call_order.append("stop")
            return make_tracking_result()

        mock_tracking.start.side_effect = start_side_effect
        mock_tracking.stop.side_effect = stop_side_effect

        service = TrackerService()
        with service.track_context():
            call_order.append("body")

        assert call_order == ["start", "body", "stop"]
