"""Infrastructure layer: C extension binding.

Converts raw dicts from archcheck._tracking to domain objects.
Stateless adapter, FAIL-FIRST on invalid data.
"""

from __future__ import annotations

from archcheck import _tracking
from archcheck.domain.events import (
    ArgInfo,
    CallEvent,
    CreateEvent,
    CreationInfo,
    DestroyEvent,
    Event,
    EventType,
    FieldError,
    Location,
    OutputError,
    ReturnEvent,
    TrackingResult,
)
from archcheck.domain.exceptions import ConversionError


def start() -> None:
    """Start tracking.

    Raises:
        RuntimeError: Already started.
    """
    _tracking.start()


def stop() -> TrackingResult:
    """Stop tracking and return all events.

    Raises:
        RuntimeError: Not started.
        KeyError: Missing required field in C output.
        ConversionError: Invalid type in C output.
    """
    raw = _tracking.stop()
    return _convert_result(raw)


def count() -> int:
    """Current event count."""
    result: int = _tracking.count()
    return result


def is_active() -> bool:
    """Is tracking active."""
    result: bool = _tracking.is_active()
    return result


def get_origin(obj: object) -> CreationInfo | None:
    """Get creation info for object.

    Raises:
        RuntimeError: Tracking not active.
        KeyError: Missing required field in C output.
        ConversionError: Invalid type in C output.
    """
    raw = _tracking.get_origin(obj)
    if raw is None:
        return None
    return _convert_creation_info(raw)


# =============================================================================
# Conversion functions (dict → domain)
# =============================================================================


def _convert_location(raw: dict[str, object]) -> Location:
    """Convert raw dict to Location. FAIL-FIRST on missing/invalid fields."""
    return Location(
        file=_str_or_none(raw["file"]),
        line=_int(raw["line"]),
        func=_str_or_none(raw["func"]),
    )


def _convert_location_optional(raw: dict[str, object], prefix: str) -> Location | None:
    """Convert optional location (caller_file, caller_line, caller_func)."""
    file_key = f"{prefix}_file"
    if file_key not in raw:
        return None
    return Location(
        file=_str_or_none(raw[file_key]),
        line=_int(raw[f"{prefix}_line"]),
        func=_str_or_none(raw[f"{prefix}_func"]),
    )


def _convert_arg_info(raw: dict[str, object]) -> ArgInfo:
    """Convert raw dict to ArgInfo."""
    return ArgInfo(
        name=_str_or_none(raw["name"]),
        obj_id=_int(raw["id"]),
        type_name=_str_or_none(raw["type"]),
    )


def _convert_field_error(raw: dict[str, object]) -> FieldError:
    """Convert raw dict to FieldError."""
    return FieldError(
        field=_str(raw["field"]),
        exc_type=_str(raw["type"]),
        exc_msg=_str(raw["message"]),
    )


def _convert_output_error(raw: dict[str, object]) -> OutputError:
    """Convert raw dict to OutputError."""
    return OutputError(
        context=_str(raw["context"]),
        exc_type=_str(raw["type"]),
        exc_msg=_str(raw["message"]),
    )


def _convert_creation_info(raw: dict[str, object]) -> CreationInfo:
    """Convert raw dict to CreationInfo."""
    traceback_raw = raw.get("traceback")
    traceback = (
        ()
        if traceback_raw is None
        else tuple(_convert_location(frame) for frame in _list_of_dicts(traceback_raw))
    )

    return CreationInfo(
        location=Location(
            file=_str_or_none(raw["file"]),
            line=_int(raw["line"]),
            func=_str_or_none(raw["func"]),
        ),
        type_name=_str_or_none(raw.get("type")),
        traceback=traceback,
    )


def _convert_event(raw: dict[str, object]) -> Event:
    """Convert raw dict to Event. Dispatches by event type."""
    event_type = EventType(_str(raw["event"]))
    location = _convert_location(raw)

    match event_type:
        case EventType.CALL:
            args_raw = raw.get("args")
            args = (
                ()
                if args_raw is None
                else tuple(_convert_arg_info(arg) for arg in _list_of_dicts(args_raw))
            )

            errors_raw = raw.get("errors")
            errors = (
                ()
                if errors_raw is None
                else tuple(_convert_field_error(err) for err in _list_of_dicts(errors_raw))
            )

            return CallEvent(
                location=location,
                caller=_convert_location_optional(raw, "caller"),
                args=args,
                errors=errors,
            )

        case EventType.RETURN:
            return ReturnEvent(
                location=location,
                return_id=_int_or_none(raw.get("return_id")),
                return_type=_str_or_none(raw.get("return_type")),
            )

        case EventType.CREATE:
            return CreateEvent(
                location=location,
                obj_id=_int(raw["id"]),
                type_name=_str(raw["type"]),
            )

        case EventType.DESTROY:
            creation_raw = raw.get("creation")
            creation = None if creation_raw is None else _convert_creation_info(_dict(creation_raw))

            return DestroyEvent(
                location=location,
                obj_id=_int(raw["id"]),
                type_name=_str(raw["type"]),
                creation=creation,
            )


def _convert_result(raw: dict[str, object]) -> TrackingResult:
    """Convert raw dict to TrackingResult."""
    events = tuple(_convert_event(ev) for ev in _list_of_dicts(raw["events"]))

    output_errors_raw = raw.get("output_errors")
    output_errors = (
        ()
        if output_errors_raw is None
        else tuple(_convert_output_error(err) for err in _list_of_dicts(output_errors_raw))
    )

    return TrackingResult(
        events=events,
        output_errors=output_errors,
    )


# =============================================================================
# Type extractors (FAIL-FIRST)
# =============================================================================


def _str(value: object) -> str:
    """Extract str. Raises ConversionError if not str."""
    if not isinstance(value, str):
        raise ConversionError(expected="str", got=type(value))
    return value


def _str_or_none(value: object) -> str | None:
    """Extract str or None. Raises ConversionError if other type."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConversionError(expected="str | None", got=type(value))
    return value


def _int(value: object) -> int:
    """Extract int. Raises ConversionError if not int."""
    if not isinstance(value, int):
        raise ConversionError(expected="int", got=type(value))
    return value


def _int_or_none(value: object) -> int | None:
    """Extract int or None. Raises ConversionError if other type."""
    if value is None:
        return None
    if not isinstance(value, int):
        raise ConversionError(expected="int | None", got=type(value))
    return value


def _dict(value: object) -> dict[str, object]:
    """Extract dict. Raises ConversionError if not dict."""
    if not isinstance(value, dict):
        raise ConversionError(expected="dict", got=type(value))
    return value


def _list_of_dicts(value: object) -> list[dict[str, object]]:
    """Extract list of dicts. Raises ConversionError if invalid."""
    if not isinstance(value, list):
        raise ConversionError(expected="list", got=type(value))
    for item in value:
        if not isinstance(item, dict):
            raise ConversionError(expected="dict", got=type(item))
    return value
