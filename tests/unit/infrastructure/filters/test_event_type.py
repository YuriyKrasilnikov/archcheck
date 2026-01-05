"""Tests for event_type filters.

Tests:
- include_types: filter by EventType whitelist
- exclude_types: filter by EventType blacklist
"""

from archcheck.domain.events import EventType
from archcheck.infrastructure.filters.event_type import exclude_types, include_types
from tests.factories import (
    make_call_event,
    make_create_event,
    make_destroy_event,
    make_return_event,
)


class TestIncludeTypes:
    """Tests for include_types filter."""

    def test_include_single_type(self) -> None:
        """include_types filters to single event type."""
        flt = include_types(EventType.CALL)

        assert flt(make_call_event()) is True
        assert flt(make_return_event()) is False
        assert flt(make_create_event()) is False
        assert flt(make_destroy_event()) is False

    def test_include_multiple_types(self) -> None:
        """include_types filters to multiple event types."""
        flt = include_types(EventType.CALL, EventType.RETURN)

        assert flt(make_call_event()) is True
        assert flt(make_return_event()) is True
        assert flt(make_create_event()) is False
        assert flt(make_destroy_event()) is False

    def test_include_all_types(self) -> None:
        """include_types with all types accepts everything."""
        flt = include_types(EventType.CALL, EventType.RETURN, EventType.CREATE, EventType.DESTROY)

        assert flt(make_call_event()) is True
        assert flt(make_return_event()) is True
        assert flt(make_create_event()) is True
        assert flt(make_destroy_event()) is True


class TestExcludeTypes:
    """Tests for exclude_types filter."""

    def test_exclude_single_type(self) -> None:
        """exclude_types excludes single event type."""
        flt = exclude_types(EventType.CREATE)

        assert flt(make_call_event()) is True
        assert flt(make_return_event()) is True
        assert flt(make_create_event()) is False
        assert flt(make_destroy_event()) is True

    def test_exclude_multiple_types(self) -> None:
        """exclude_types excludes multiple event types."""
        flt = exclude_types(EventType.CREATE, EventType.DESTROY)

        assert flt(make_call_event()) is True
        assert flt(make_return_event()) is True
        assert flt(make_create_event()) is False
        assert flt(make_destroy_event()) is False

    def test_exclude_all_types(self) -> None:
        """exclude_types with all types rejects everything."""
        flt = exclude_types(
            EventType.CALL,
            EventType.RETURN,
            EventType.CREATE,
            EventType.DESTROY,
        )

        assert flt(make_call_event()) is False
        assert flt(make_return_event()) is False
        assert flt(make_create_event()) is False
        assert flt(make_destroy_event()) is False
