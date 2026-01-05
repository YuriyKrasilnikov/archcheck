"""Console reporter: TrackingResult → rich formatted string."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING

from rich.console import Console

from archcheck.application.reporters.strategies import (
    ByTypeStrategy,
    GroupStrategy,
    format_location_short,
)
from archcheck.domain.events import (
    CreateEvent,
    DestroyEvent,
    EventType,
    get_event_type,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from archcheck.domain.events import Event, TrackingResult


@dataclass(frozen=True, slots=True)
class ConsoleConfig:
    """Configuration for console reporter.

    All fields have defaults (convenience).
    User can override any field (No Special Cases per PHILOSOPHY).
    Immutable (frozen dataclass).

    Attributes:
        show_lifecycle: Show object CREATE→DESTROY pairs section.
        show_traceback: Show traceback in lifecycle section.
        max_events: Max events to display. None = unlimited (Data Completeness).
        group_by: Strategy for grouping events. None = ByTypeStrategy().
        include_types: Event types to include. None = all types.
        exclude_paths: Glob patterns for files to exclude.
    """

    show_lifecycle: bool = True
    show_traceback: bool = True
    max_events: int | None = None
    group_by: GroupStrategy | None = None
    include_types: frozenset[EventType] | None = None
    exclude_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Summary:
    """Internal summary statistics."""

    total: int
    by_type: Mapping[str, int]


class ConsoleReporter:
    """Console reporter: outputs rich formatted text.

    Output is str, not print(). Caller decides destination.
    Data Completeness: shows ALL data unless user explicitly limits via config.
    """

    def __init__(self, config: ConsoleConfig | None = None) -> None:
        """Initialize reporter.

        Args:
            config: Reporter configuration. Uses defaults if None.
        """
        self._config = config or ConsoleConfig()

    def report(self, result: TrackingResult) -> str:
        """Format tracking result as rich formatted string.

        Args:
            result: Tracking result to format.

        Returns:
            Formatted string with colors and tables.
        """
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        events = self._filter_events(result.events)
        summary = self._build_summary(events)

        self._render_header(console, summary)
        self._render_events(console, events)

        if self._config.show_lifecycle:
            self._render_lifecycle(console, events)

        if result.output_errors:
            self._render_errors(console, result)

        return output.getvalue()

    def _filter_events(self, events: tuple[Event, ...]) -> tuple[Event, ...]:
        """Filter events by config. Only explicit config filters applied."""
        filtered: list[Event] = []

        for event in events:
            if self._config.max_events is not None and len(filtered) >= self._config.max_events:
                break

            event_type = get_event_type(event)
            if self._config.include_types and event_type not in self._config.include_types:
                continue

            if self._config.exclude_paths:
                file_path = event.location.file or ""
                if any(fnmatch.fnmatch(file_path, p) for p in self._config.exclude_paths):
                    continue

            filtered.append(event)

        return tuple(filtered)

    def _build_summary(self, events: tuple[Event, ...]) -> _Summary:
        """Build summary statistics."""
        by_type: dict[str, int] = {}
        for event in events:
            type_name = get_event_type(event).value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        return _Summary(total=len(events), by_type=by_type)

    def _render_header(self, console: Console, summary: _Summary) -> None:
        """Render header with summary."""
        console.print()
        console.rule("[bold]TRACKING RESULT[/bold]")
        console.print()

        parts = [f"[bold]Events:[/bold] {summary.total}"]
        if summary.by_type:
            type_parts = [f"{k}: {v}" for k, v in sorted(summary.by_type.items())]
            parts.append(f"({', '.join(type_parts)})")

        console.print(" ".join(parts))
        console.print()

    def _render_events(self, console: Console, events: tuple[Event, ...]) -> None:
        """Render events using configured strategy."""
        strategy = self._config.group_by or ByTypeStrategy()
        grouped = strategy.group(events)
        strategy.render(console, grouped)

    def _render_lifecycle(self, console: Console, events: tuple[Event, ...]) -> None:
        """Render object lifecycle (CREATE → DESTROY pairs)."""
        creates: dict[int, CreateEvent] = {}
        destroys: dict[int, DestroyEvent] = {}

        for event in events:
            match event:
                case CreateEvent():
                    creates[event.obj_id] = event
                case DestroyEvent():
                    destroys[event.obj_id] = event

        paired_ids = set(creates.keys()) & set(destroys.keys())
        if not paired_ids:
            return

        console.print("[bold]OBJECT LIFECYCLE[/bold]")
        console.print()

        for obj_id in paired_ids:
            create = creates[obj_id]
            destroy = destroys[obj_id]

            console.print(f"[yellow]{create.type_name}[/yellow] (id={obj_id}):")
            console.print(f"  CREATE  {format_location_short(create.location)}")
            console.print(f"  DESTROY {format_location_short(destroy.location)}")

            if self._config.show_traceback and destroy.creation:
                console.print("  [dim]Traceback at creation:[/dim]")
                for frame in destroy.creation.traceback:
                    console.print(f"    {format_location_short(frame)}")

            console.print()

    def _render_errors(self, console: Console, result: TrackingResult) -> None:
        """Render output errors."""
        console.print(f"[bold red]OUTPUT ERRORS[/bold red] ({len(result.output_errors)})")
        console.print()

        for error in result.output_errors:
            console.print(f"  [{error.context}] {error.exc_type}: {error.exc_msg}")

        console.print()
