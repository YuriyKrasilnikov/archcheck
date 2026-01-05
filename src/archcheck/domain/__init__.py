"""Domain layer: immutable value objects with invariant validation."""

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
    get_event_type,
)
from archcheck.domain.exceptions import (
    AlreadyActiveError,
    ArchCheckError,
    ConversionError,
    NotExitedError,
)

__all__ = [
    "AlreadyActiveError",
    "ArchCheckError",
    "ArgInfo",
    "CallEvent",
    "ConversionError",
    "CreateEvent",
    "CreationInfo",
    "DestroyEvent",
    "Event",
    "EventType",
    "FieldError",
    "Location",
    "NotExitedError",
    "OutputError",
    "ReturnEvent",
    "TrackingResult",
    "get_event_type",
]
