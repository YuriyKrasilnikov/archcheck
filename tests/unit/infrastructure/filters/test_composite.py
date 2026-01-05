"""Tests for composite filters.

Tests:
- all_of: AND composition
- any_of: OR composition
- negate: NOT operator
"""

from archcheck.domain.events import EventType
from archcheck.infrastructure.filters.composite import all_of, any_of, negate
from archcheck.infrastructure.filters.event_type import exclude_types, include_types
from archcheck.infrastructure.filters.path import include_paths
from tests.factories import make_call_event, make_create_event


class TestAllOf:
    """Tests for all_of (AND) filter composition."""

    def test_all_of_all_pass(self) -> None:
        """all_of passes when all filters pass."""
        flt = all_of(
            include_types(EventType.CALL),
            include_paths("src/*"),
        )

        # CALL event with src/ path - both filters pass
        assert flt(make_call_event(file="src/main.py")) is True

    def test_all_of_one_fails(self) -> None:
        """all_of fails when any filter fails."""
        flt = all_of(
            include_types(EventType.CALL),
            include_paths("src/*"),
        )

        # CALL event but wrong path
        assert flt(make_call_event(file="lib/main.py")) is False

        # Right path but wrong event type
        assert flt(make_create_event(file="src/main.py")) is False

    def test_all_of_empty(self) -> None:
        """all_of with no filters passes everything."""
        flt = all_of()

        assert flt(make_call_event()) is True
        assert flt(make_create_event()) is True

    def test_all_of_single(self) -> None:
        """all_of with single filter behaves as that filter."""
        flt = all_of(include_types(EventType.CALL))

        assert flt(make_call_event()) is True
        assert flt(make_create_event()) is False


class TestAnyOf:
    """Tests for any_of (OR) filter composition."""

    def test_any_of_one_passes(self) -> None:
        """any_of passes when any filter passes."""
        flt = any_of(
            include_types(EventType.CALL),
            include_types(EventType.CREATE),
        )

        assert flt(make_call_event()) is True
        assert flt(make_create_event()) is True

    def test_any_of_none_pass(self) -> None:
        """any_of fails when all filters fail."""
        flt = any_of(
            include_types(EventType.CALL),
            include_paths("src/*"),
        )

        # CREATE event with lib/ path - both filters fail
        assert flt(make_create_event(file="lib/main.py")) is False

    def test_any_of_empty(self) -> None:
        """any_of with no filters fails everything."""
        flt = any_of()

        assert flt(make_call_event()) is False
        assert flt(make_create_event()) is False

    def test_any_of_single(self) -> None:
        """any_of with single filter behaves as that filter."""
        flt = any_of(include_types(EventType.CALL))

        assert flt(make_call_event()) is True
        assert flt(make_create_event()) is False


class TestNegate:
    """Tests for negate (NOT) filter."""

    def test_negate_inverts(self) -> None:
        """Negate inverts filter result."""
        flt = negate(include_types(EventType.CALL))

        assert flt(make_call_event()) is False  # was True
        assert flt(make_create_event()) is True  # was False

    def test_negate_exclude(self) -> None:
        """Negate on exclude becomes include."""
        flt = negate(exclude_types(EventType.CREATE))

        # exclude_types(CREATE) returns False for CREATE
        # negate makes it True
        assert flt(make_create_event()) is True
        assert flt(make_call_event()) is False


class TestComposition:
    """Tests for complex filter compositions."""

    def test_nested_composition(self) -> None:
        """Filters can be nested arbitrarily."""
        # Include CALL events from src/ OR any CREATE events
        flt = any_of(
            all_of(include_types(EventType.CALL), include_paths("src/*")),
            include_types(EventType.CREATE),
        )

        assert flt(make_call_event(file="src/main.py")) is True  # CALL + src/
        assert flt(make_call_event(file="lib/main.py")) is False  # CALL but not src/
        assert flt(make_create_event(file="lib/main.py")) is True  # CREATE anywhere
