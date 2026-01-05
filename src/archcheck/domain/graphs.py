"""Domain layer: graph structures for call analysis.

Immutable value objects with invariant validation.
FAIL-FIRST: invalid input raises immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from archcheck.domain.events import (
        CallEvent,
        CreateEvent,
        DestroyEvent,
        EventType,
        Location,
        ReturnEvent,
        TrackingResult,
    )


@dataclass(frozen=True, slots=True)
class CallEdge:
    """Edge in call graph: caller → callee with invocation count.

    Invariants:
        - count >= 1 (FAIL-FIRST in __post_init__)

    Note: self-loops (caller == callee) filtered during CallGraph construction,
    not here. CallEdge is a value object, validation at construction level.
    """

    caller: Location
    callee: Location
    count: int

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST on invalid count."""
        if self.count < 1:
            msg = f"count must be >= 1, got {self.count}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class CallGraph:
    """Call graph: edges between functions with unmatched events.

    Data Completeness: unmatched stores orphan CALL/RETURN events
    (CALL without matching RETURN, or RETURN without matching CALL).

    Invariants:
        - edges is frozenset (immutable)
        - unmatched is tuple (immutable, ordered by capture time)
    """

    edges: frozenset[CallEdge]
    unmatched: tuple[CallEvent | ReturnEvent, ...]


@dataclass(frozen=True, slots=True)
class ObjectLifecycle:
    """Lifecycle of a single tracked object.

    Tracks creation, optional destruction, and all locations where passed.

    Invariants:
        - created always present
        - destroyed.obj_id == obj_id (if destroyed present, FAIL-FIRST)
    """

    obj_id: int
    type_name: str
    created: CreateEvent
    destroyed: DestroyEvent | None
    locations: tuple[Location, ...]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST on obj_id mismatch."""
        if self.destroyed is not None and self.destroyed.obj_id != self.obj_id:
            msg = f"obj_id mismatch: lifecycle={self.obj_id}, destroyed={self.destroyed.obj_id}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ObjectFlow:
    """Object flow: all tracked object lifecycles with orphan destroys.

    Data Completeness: orphan_destroys stores DESTROY events without
    matching CREATE (object created before tracking started).

    Invariants:
        - objects maps obj_id → ObjectLifecycle
        - orphan_destroys is tuple (immutable, ordered by capture time)
    """

    objects: Mapping[int, ObjectLifecycle]
    orphan_destroys: tuple[DestroyEvent, ...]


@dataclass(frozen=True, slots=True)
class FilterConfig:
    """Configuration for event filtering.

    Per PHILOSOPHY:
        - All fields optional (empty = no filter)
        - User can replace any default (No Special Cases)
        - Immutable (frozen dataclass)

    Attributes:
        include_paths: Glob patterns for files to include. Empty = all files.
        exclude_paths: Glob patterns for files to exclude. Applied after include.
        include_types: Event types to include. None = all types.
    """

    include_paths: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = ()
    include_types: frozenset[EventType] | None = None


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Result of analysis: filtered events, call graph, and object flow.

    Produced by AnalyzerService.analyze().
    Immutable composition of all analysis artifacts.
    """

    filtered: TrackingResult
    call_graph: CallGraph
    object_flow: ObjectFlow
