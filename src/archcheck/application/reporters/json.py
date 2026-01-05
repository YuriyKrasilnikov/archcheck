"""JSON reporter: TrackingResult → JSON string."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from archcheck.domain.events import (
    CallEvent,
    CreateEvent,
    DestroyEvent,
    EventType,
    ReturnEvent,
    get_event_type,
)

if TYPE_CHECKING:
    from archcheck.domain.events import (
        ArgInfo,
        CreationInfo,
        Event,
        FieldError,
        Location,
        OutputError,
        TrackingResult,
    )


class JsonReporter:
    """JSON reporter: outputs machine-readable JSON.

    Schema matches domain structure 1:1 with summary added.
    """

    def __init__(self, *, indent: int | None = 2) -> None:
        """Initialize reporter.

        Args:
            indent: JSON indentation. None for compact output.
        """
        self._indent = indent

    def report(self, result: TrackingResult) -> str:
        """Format tracking result as JSON string.

        Args:
            result: Tracking result to format.

        Returns:
            JSON string with events, errors, and summary.
        """
        data = {
            "events": [_event_to_dict(e) for e in result.events],
            "output_errors": [_output_error_to_dict(e) for e in result.output_errors],
            "summary": _build_summary(result),
        }
        return json.dumps(data, indent=self._indent)


def _build_summary(result: TrackingResult) -> dict[str, object]:
    """Build summary statistics."""
    by_type: dict[str, int] = {}
    for event in result.events:
        type_name = get_event_type(event).value
        by_type[type_name] = by_type.get(type_name, 0) + 1

    return {
        "total": len(result.events),
        "by_type": by_type,
    }


def _location_to_dict(loc: Location) -> dict[str, object]:
    """Convert Location to dict."""
    return {
        "file": loc.file,
        "line": loc.line,
        "func": loc.func,
    }


def _arg_info_to_dict(arg: ArgInfo) -> dict[str, object]:
    """Convert ArgInfo to dict."""
    return {
        "name": arg.name,
        "id": arg.obj_id,
        "type": arg.type_name,
    }


def _field_error_to_dict(err: FieldError) -> dict[str, object]:
    """Convert FieldError to dict."""
    return {
        "field": err.field,
        "type": err.exc_type,
        "message": err.exc_msg,
    }


def _output_error_to_dict(err: OutputError) -> dict[str, object]:
    """Convert OutputError to dict."""
    return {
        "context": err.context,
        "type": err.exc_type,
        "message": err.exc_msg,
    }


def _creation_info_to_dict(info: CreationInfo) -> dict[str, object]:
    """Convert CreationInfo to dict."""
    return {
        "location": _location_to_dict(info.location),
        "type_name": info.type_name,
        "traceback": [_location_to_dict(loc) for loc in info.traceback],
    }


def _event_to_dict(event: Event) -> dict[str, object]:
    """Convert Event to dict."""
    match event:
        case CallEvent():
            return {
                "type": EventType.CALL.value,
                "location": _location_to_dict(event.location),
                "caller": _location_to_dict(event.caller) if event.caller else None,
                "args": [_arg_info_to_dict(a) for a in event.args],
                "errors": [_field_error_to_dict(e) for e in event.errors],
            }
        case ReturnEvent():
            return {
                "type": EventType.RETURN.value,
                "location": _location_to_dict(event.location),
                "return_id": event.return_id,
                "return_type": event.return_type,
            }
        case CreateEvent():
            return {
                "type": EventType.CREATE.value,
                "location": _location_to_dict(event.location),
                "obj_id": event.obj_id,
                "type_name": event.type_name,
            }
        case DestroyEvent():
            return {
                "type": EventType.DESTROY.value,
                "location": _location_to_dict(event.location),
                "obj_id": event.obj_id,
                "type_name": event.type_name,
                "creation": _creation_info_to_dict(event.creation) if event.creation else None,
            }
