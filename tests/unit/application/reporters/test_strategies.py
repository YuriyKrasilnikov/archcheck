"""Tests for GroupStrategy implementations.

Tests:
- get_event_type for all event types
- format_location_short formatting
- ByTypeStrategy grouping and rendering
- ByFileStrategy grouping and rendering
- ByFuncStrategy grouping and rendering
- Custom strategy implementation by user
"""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from archcheck.domain.events import Event

from archcheck.application.reporters.strategies import (
    ByFileStrategy,
    ByFuncStrategy,
    ByTypeStrategy,
    GroupStrategy,
    format_location_short,
)
from tests.factories import (
    make_call_event,
    make_create_event,
    make_location,
    make_return_event,
)


class TestFormatLocationShort:
    """Tests for format_location_short function."""

    def test_full_location_formats_correctly(self) -> None:
        """Full location -> file:line func."""
        loc = make_location(file="src/app/service.py", line=42, func="handle")
        assert format_location_short(loc) == "service.py:42 handle"

    def test_none_file_shows_question_mark(self) -> None:
        """file=None -> '?' instead of filename."""
        loc = make_location(file=None, line=10, func="test")
        assert format_location_short(loc) == "?:10 test"

    def test_none_func_shows_question_mark(self) -> None:
        """func=None -> '?' instead of function name."""
        loc = make_location(file="test.py", line=5, func=None)
        assert format_location_short(loc) == "test.py:5 ?"


class TestByTypeStrategy:
    """Tests for ByTypeStrategy."""

    def test_groups_events_by_event_type(self) -> None:
        """Events are grouped by type (CALL, RETURN, CREATE, DESTROY)."""
        events = (
            make_call_event(),
            make_return_event(),
            make_call_event(line=11),
            make_create_event(),
        )
        strategy = ByTypeStrategy()
        grouped = strategy.group(events)

        assert "CALL" in grouped
        assert "RETURN" in grouped
        assert "CREATE" in grouped
        assert len(grouped["CALL"]) == 2
        assert len(grouped["RETURN"]) == 1
        assert len(grouped["CREATE"]) == 1

    def test_empty_events_returns_empty_dict(self) -> None:
        """Empty events tuple -> empty dict."""
        strategy = ByTypeStrategy()
        grouped = strategy.group(())
        assert grouped == {}

    def test_render_outputs_event_sections(self) -> None:
        """render() outputs sections by event type."""
        events = (make_call_event(), make_return_event())
        strategy = ByTypeStrategy()
        grouped = strategy.group(events)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        strategy.render(console, grouped)

        result = output.getvalue()
        assert "CALL EVENTS" in result
        assert "RETURN EVENTS" in result

    def test_show_args_true_by_default(self) -> None:
        """show_args=True by default."""
        strategy = ByTypeStrategy()
        assert strategy.show_args is True

    def test_show_args_can_be_disabled(self) -> None:
        """show_args can be disabled on creation."""
        strategy = ByTypeStrategy(show_args=False)
        assert strategy.show_args is False

    def test_show_caller_true_by_default(self) -> None:
        """show_caller=True by default."""
        strategy = ByTypeStrategy()
        assert strategy.show_caller is True


class TestByFileStrategy:
    """Tests for ByFileStrategy."""

    def test_groups_events_by_file_path(self) -> None:
        """Events are grouped by file path."""
        events = (
            make_call_event(file="a.py"),
            make_call_event(file="b.py"),
            make_return_event(file="a.py"),
        )
        strategy = ByFileStrategy()
        grouped = strategy.group(events)

        assert "a.py" in grouped
        assert "b.py" in grouped
        assert len(grouped["a.py"]) == 2
        assert len(grouped["b.py"]) == 1

    def test_none_file_grouped_as_unknown(self) -> None:
        """file=None is grouped as '<unknown>'."""
        events = (make_call_event(file=None),)
        strategy = ByFileStrategy()
        grouped = strategy.group(events)

        assert "<unknown>" in grouped

    def test_render_outputs_file_sections(self) -> None:
        """render() outputs sections by file."""
        events = (make_call_event(file="test.py"),)
        strategy = ByFileStrategy()
        grouped = strategy.group(events)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        strategy.render(console, grouped)

        result = output.getvalue()
        assert "test.py" in result


class TestByFuncStrategy:
    """Tests for ByFuncStrategy."""

    def test_groups_events_by_function_name(self) -> None:
        """Events are grouped by function name."""
        events = (
            make_call_event(func="foo"),
            make_call_event(func="bar"),
            make_return_event(func="foo"),
        )
        strategy = ByFuncStrategy()
        grouped = strategy.group(events)

        assert "foo" in grouped
        assert "bar" in grouped
        assert len(grouped["foo"]) == 2
        assert len(grouped["bar"]) == 1

    def test_none_func_grouped_as_unknown(self) -> None:
        """func=None is grouped as '<unknown>'."""
        events = (make_call_event(func=None),)
        strategy = ByFuncStrategy()
        grouped = strategy.group(events)

        assert "<unknown>" in grouped

    def test_render_outputs_function_sections(self) -> None:
        """render() outputs sections by function."""
        events = (make_call_event(func="my_func"),)
        strategy = ByFuncStrategy()
        grouped = strategy.group(events)

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        strategy.render(console, grouped)

        result = output.getvalue()
        assert "my_func" in result


class TestCustomStrategy:
    """Tests for custom user-defined strategy."""

    def test_custom_strategy_satisfies_protocol(self) -> None:
        """User can create custom strategy implementing GroupStrategy Protocol."""

        class ByLineStrategy:
            """Groups events by line number."""

            def group(self, events: tuple[Event, ...]) -> dict[str, list[Event]]:
                """Group by line number."""
                by_line: dict[str, list[Event]] = {}
                for event in events:
                    key = str(event.location.line)
                    by_line.setdefault(key, []).append(event)
                return by_line

            def render(self, console: Console, grouped: dict[str, list[Event]]) -> None:
                """Render by line number."""
                for line, line_events in sorted(grouped.items()):
                    console.print(f"Line {line}: {len(line_events)} events")

        events = (
            make_call_event(line=10),
            make_call_event(line=20),
            make_return_event(line=10),
        )

        strategy: GroupStrategy = ByLineStrategy()
        grouped = strategy.group(events)

        assert "10" in grouped
        assert "20" in grouped
        assert len(grouped["10"]) == 2
        assert len(grouped["20"]) == 1
