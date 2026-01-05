"""Domain layer: immutable value objects for tracking events.

Maps 1:1 to C types from c/tracking/types.h.
All objects frozen, invariants validated in __post_init__.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    """Event types from C EventType enum."""

    CALL = "CALL"
    RETURN = "RETURN"
    CREATE = "CREATE"
    DESTROY = "DESTROY"


@dataclass(frozen=True, slots=True)
class Location:
    """Frame location (file, line, func).

    Maps to C FrameInfo struct.
    Invariants validated at conversion time in infrastructure layer.
    """

    file: str | None
    line: int
    func: str | None


@dataclass(frozen=True, slots=True)
class ArgInfo:
    """Argument info for CALL events.

    Maps to C ArgInfo struct.
    """

    name: str | None
    obj_id: int
    type_name: str | None


@dataclass(frozen=True, slots=True)
class FieldError:
    """Error captured during event collection.

    Maps to C FieldError struct.
    Example: UnicodeDecodeError when extracting filename.
    """

    field: str
    exc_type: str
    exc_msg: str


@dataclass(frozen=True, slots=True)
class OutputError:
    """Error captured during serialization in stop().

    Maps to C OutputError struct.
    Example: Memory allocation failure when building Python dict.
    """

    context: str
    exc_type: str
    exc_msg: str


@dataclass(frozen=True, slots=True)
class CreationInfo:
    """Object creation info stored in hash table.

    Maps to C CreationInfo struct.
    Includes full traceback at creation time.
    """

    location: Location
    type_name: str | None
    traceback: tuple[Location, ...]


@dataclass(frozen=True, slots=True)
class CallEvent:
    """CALL event: function entry."""

    location: Location
    caller: Location | None
    args: tuple[ArgInfo, ...]
    errors: tuple[FieldError, ...]


@dataclass(frozen=True, slots=True)
class ReturnEvent:
    """RETURN event: function exit."""

    location: Location
    return_id: int | None
    return_type: str | None


@dataclass(frozen=True, slots=True)
class CreateEvent:
    """CREATE event: object allocated."""

    location: Location
    obj_id: int
    type_name: str


@dataclass(frozen=True, slots=True)
class DestroyEvent:
    """DESTROY event: object deallocated."""

    location: Location
    obj_id: int
    type_name: str
    creation: CreationInfo | None


Event = CallEvent | ReturnEvent | CreateEvent | DestroyEvent


def get_event_type(event: Event) -> EventType:
    """Get EventType for event.

    Exhaustive match on Event union. Type system ensures all cases covered.
    """
    match event:
        case CallEvent():
            return EventType.CALL
        case ReturnEvent():
            return EventType.RETURN
        case CreateEvent():
            return EventType.CREATE
        case DestroyEvent():
            return EventType.DESTROY


@dataclass(frozen=True, slots=True)
class TrackingResult:
    """Result of stop(): all events + any output errors.

    Invariant: all captured data preserved (Data Completeness).
    """

    events: tuple[Event, ...]
    output_errors: tuple[OutputError, ...]
