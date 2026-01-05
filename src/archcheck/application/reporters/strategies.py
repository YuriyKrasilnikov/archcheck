"""Group strategies for console reporter.

GroupStrategy Protocol defines interface for grouping and rendering events.
Built-in strategies: ByTypeStrategy, ByFileStrategy, ByFuncStrategy.
User can implement custom strategies with same Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from rich.table import Table

from archcheck.domain.events import (
    CallEvent,
    CreateEvent,
    DestroyEvent,
    EventType,
    ReturnEvent,
    get_event_type,
)

if TYPE_CHECKING:
    from rich.console import Console

    from archcheck.domain.events import Event, Location


class GroupStrategy(Protocol):
    """Protocol for event grouping and rendering.

    User can implement custom strategies by satisfying this Protocol.
    Built-in strategies are NOT special - same interface, same status.
    """

    def group(self, events: tuple[Event, ...]) -> dict[str, list[Event]]:
        """Group events by strategy-specific key.

        Args:
            events: Events to group.

        Returns:
            Dict mapping group key to list of events.
        """
        ...

    def render(self, console: Console, grouped: dict[str, list[Event]]) -> None:
        """Render grouped events to console.

        Args:
            console: Rich console for output.
            grouped: Events grouped by key.
        """
        ...


def format_location_short(loc: Location) -> str:
    """Format location as short string: file:line func."""
    file_part = loc.file.split("/")[-1] if loc.file else "?"
    func_part = loc.func or "?"
    return f"{file_part}:{loc.line} {func_part}"


@dataclass(frozen=True, slots=True)
class ByTypeStrategy:
    """Group events by EventType (CALL, RETURN, CREATE, DESTROY).

    Attributes:
        show_args: Show function arguments in CALL events.
        show_caller: Show caller location in CALL events.
    """

    show_args: bool = True
    show_caller: bool = True

    def group(self, events: tuple[Event, ...]) -> dict[str, list[Event]]:
        """Group events by event type."""
        by_type: dict[str, list[Event]] = {}
        for event in events:
            key = get_event_type(event).value
            by_type.setdefault(key, []).append(event)
        return by_type

    def render(self, console: Console, grouped: dict[str, list[Event]]) -> None:
        """Render events grouped by type with tables."""
        for event_type in EventType:
            events = grouped.get(event_type.value, [])
            if not events:
                continue

            console.print(f"[bold]{event_type.value} EVENTS[/bold] ({len(events)})")
            table = self._create_table(event_type)

            for event in events:
                self._add_row(table, event)

            console.print(table)
            console.print()

    def _create_table(self, event_type: EventType) -> Table:
        """Create table for event type."""
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("Location", style="cyan")

        match event_type:
            case EventType.CALL:
                table.add_column("Function")
                if self.show_caller:
                    table.add_column("Caller", style="dim")
                if self.show_args:
                    table.add_column("Args", style="dim")
            case EventType.RETURN:
                table.add_column("Function")
                table.add_column("Return", style="green")
            case EventType.CREATE:
                table.add_column("Type", style="yellow")
                table.add_column("ID", style="dim")
            case EventType.DESTROY:
                table.add_column("Type", style="yellow")
                table.add_column("ID", style="dim")

        return table

    def _add_row(self, table: Table, event: Event) -> None:
        """Add event row to table."""
        loc = format_location_short(event.location)

        match event:
            case CallEvent():
                func = event.location.func or "<unknown>"
                row: list[str] = [loc, func]
                if self.show_caller:
                    caller = format_location_short(event.caller) if event.caller else "-"
                    row.append(caller)
                if self.show_args:
                    args = ", ".join(f"{a.name}:{a.type_name}" for a in event.args)
                    row.append(args or "-")
                table.add_row(*row)
            case ReturnEvent():
                func = event.location.func or "<unknown>"
                ret = event.return_type or "-"
                table.add_row(loc, func, ret)
            case CreateEvent():
                table.add_row(loc, event.type_name, str(event.obj_id))
            case DestroyEvent():
                table.add_row(loc, event.type_name, str(event.obj_id))


@dataclass(frozen=True, slots=True)
class ByFileStrategy:
    """Group events by source file."""

    def group(self, events: tuple[Event, ...]) -> dict[str, list[Event]]:
        """Group events by file path."""
        by_file: dict[str, list[Event]] = {}
        for event in events:
            key = event.location.file or "<unknown>"
            by_file.setdefault(key, []).append(event)
        return by_file

    def render(self, console: Console, grouped: dict[str, list[Event]]) -> None:
        """Render events grouped by file."""
        for file_path, events in sorted(grouped.items()):
            console.print(f"[bold]{file_path}[/bold]")
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("line", style="dim")
            table.add_column("type", style="cyan")
            table.add_column("details")

            for event in events:
                event_type = get_event_type(event)
                details = self._format_details(event)
                table.add_row(f":{event.location.line}", event_type.value, details)

            console.print(table)
            console.print()

    def _format_details(self, event: Event) -> str:
        """Format event details for single-line display."""
        match event:
            case CallEvent():
                func = event.location.func or "?"
                caller = event.caller.func if event.caller else None
                return f"{func} ← {caller}" if caller else func
            case ReturnEvent():
                func = event.location.func or "?"
                return f"{func} → {event.return_type or '?'}"
            case CreateEvent():
                return f"{event.type_name} id={event.obj_id}"
            case DestroyEvent():
                return f"{event.type_name} id={event.obj_id}"


@dataclass(frozen=True, slots=True)
class ByFuncStrategy:
    """Group events by function name."""

    def group(self, events: tuple[Event, ...]) -> dict[str, list[Event]]:
        """Group events by function name."""
        by_func: dict[str, list[Event]] = {}
        for event in events:
            key = event.location.func or "<unknown>"
            by_func.setdefault(key, []).append(event)
        return by_func

    def render(self, console: Console, grouped: dict[str, list[Event]]) -> None:
        """Render events grouped by function."""
        for func_name, events in sorted(grouped.items()):
            console.print(f"[bold]{func_name}[/bold] ({len(events)} events)")
            for event in events:
                event_type = get_event_type(event)
                loc = format_location_short(event.location)
                console.print(f"  {event_type.value:8} {loc}")
            console.print()
