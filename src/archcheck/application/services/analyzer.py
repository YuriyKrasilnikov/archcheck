"""Analyzer service: orchestrates filtering and analysis.

Produces CallGraph, ObjectFlow, and AnalysisResult from TrackingResult.
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

from archcheck.domain.events import (
    CallEvent,
    CreateEvent,
    DestroyEvent,
    ReturnEvent,
    TrackingResult,
    get_event_type,
)
from archcheck.domain.exceptions import DuplicateCreateError
from archcheck.domain.graphs import (
    AnalysisResult,
    CallEdge,
    CallGraph,
    ObjectFlow,
    ObjectLifecycle,
)

if TYPE_CHECKING:
    from archcheck.domain.events import Location
    from archcheck.domain.graphs import FilterConfig


class AnalyzerService:
    """Orchestrates event filtering and graph construction.

    Methods:
        filter(): Apply FilterConfig to TrackingResult
        build_call_graph(): Construct CallGraph from events
        build_object_flow(): Construct ObjectFlow from events
        analyze(): Full analysis pipeline
    """

    def filter(self, result: TrackingResult, config: FilterConfig) -> TrackingResult:
        """Filter events based on configuration.

        Path filters (include_paths, exclude_paths) apply ONLY to CALL/RETURN.
        CREATE/DESTROY are never filtered by path (object IDs are global).
        include_types applies to all event types.

        Args:
            result: Raw tracking result.
            config: Filter configuration.

        Returns:
            TrackingResult with filtered events, output_errors preserved.
        """
        filtered_events = tuple(e for e in result.events if self._should_include(e, config))
        return TrackingResult(events=filtered_events, output_errors=result.output_errors)

    def _should_include(
        self,
        event: CallEvent | ReturnEvent | CreateEvent | DestroyEvent,
        config: FilterConfig,
    ) -> bool:
        """Check if event passes filter config.

        Path filters apply only to CALL/RETURN (not CREATE/DESTROY).
        """
        # Type filter applies to all events
        if config.include_types is not None and get_event_type(event) not in config.include_types:
            return False

        # Path filters apply only to CALL/RETURN
        if isinstance(event, (CallEvent, ReturnEvent)):
            file_path = event.location.file
            if file_path is not None:
                # include_paths: must match at least one pattern (if specified)
                if config.include_paths and not any(
                    fnmatch.fnmatch(file_path, p) for p in config.include_paths
                ):
                    return False
                # exclude_paths: must not match any pattern
                if config.exclude_paths and any(
                    fnmatch.fnmatch(file_path, p) for p in config.exclude_paths
                ):
                    return False

        return True

    def build_call_graph(self, result: TrackingResult) -> CallGraph:
        """Build call graph from tracking result.

        Algorithm:
            1. Process events in order
            2. CALL: push to stack
            3. RETURN: pop from stack, create edge (caller → callee)
            4. Aggregate duplicate edges by incrementing count
            5. Filter self-loops (caller == callee)

        Data Completeness:
            - Unmatched CALL (no RETURN): tracked in unmatched
            - Unmatched RETURN (no CALL): tracked in unmatched

        Args:
            result: Tracking result (typically filtered).

        Returns:
            CallGraph with edges and unmatched events.
        """
        call_stack: list[CallEvent] = []
        edge_counts: dict[tuple[Location, Location], int] = {}
        unmatched: list[CallEvent | ReturnEvent] = []

        for event in result.events:
            match event:
                case CallEvent():
                    call_stack.append(event)
                case ReturnEvent():
                    if call_stack:
                        call_event = call_stack.pop()
                        caller = call_event.caller
                        callee = call_event.location

                        # Skip if no caller info (file=None) or self-loop
                        if caller is not None and caller.file is not None and caller != callee:
                            key = (caller, callee)
                            edge_counts[key] = edge_counts.get(key, 0) + 1
                    else:
                        # RETURN without matching CALL (Data Completeness)
                        unmatched.append(event)

        # Remaining CALLs on stack are unmatched (Data Completeness)
        unmatched.extend(call_stack)

        # Build edges
        edges = frozenset(
            CallEdge(caller=caller, callee=callee, count=count)
            for (caller, callee), count in edge_counts.items()
        )

        return CallGraph(edges=edges, unmatched=tuple(unmatched))

    def build_object_flow(self, result: TrackingResult) -> ObjectFlow:
        """Build object flow from tracking result.

        Algorithm:
            1. CREATE → create ObjectLifecycle entry
            2. CALL.args → track where objects are passed
            3. DESTROY → set lifecycle.destroyed

        Data Completeness:
            - DESTROY without CREATE: tracked in orphan_destroys
            - CREATE without DESTROY: lifecycle.destroyed = None

        FAIL-FIRST:
            - Multiple CREATE with same obj_id: raises ValueError

        Args:
            result: Tracking result (typically filtered).

        Returns:
            ObjectFlow with lifecycles and orphan destroys.
        """
        # Track creates: obj_id → (CreateEvent, list of locations)
        creates: dict[int, tuple[CreateEvent, list[Location]]] = {}
        orphan_destroys: list[DestroyEvent] = []

        # Completed lifecycles (CREATE + DESTROY seen)
        completed: dict[int, ObjectLifecycle] = {}

        for event in result.events:
            match event:
                case CreateEvent():
                    if event.obj_id in creates:
                        # Duplicate CREATE without DESTROY - error (C bug)
                        raise DuplicateCreateError(event.obj_id)
                    creates[event.obj_id] = (event, [])

                case DestroyEvent():
                    if event.obj_id in creates:
                        # Complete the lifecycle
                        create_event, locations = creates.pop(event.obj_id)
                        completed[event.obj_id] = ObjectLifecycle(
                            obj_id=event.obj_id,
                            type_name=create_event.type_name,
                            created=create_event,
                            destroyed=event,
                            locations=tuple(locations),
                        )
                    else:
                        # DESTROY without CREATE (Data Completeness)
                        orphan_destroys.append(event)

                case CallEvent():
                    # Track where objects are passed as arguments
                    for arg in event.args:
                        if arg.obj_id in creates:
                            creates[arg.obj_id][1].append(event.location)

        # Build lifecycles for still-alive objects (CREATE without DESTROY)
        objects: dict[int, ObjectLifecycle] = {}
        for obj_id, (create_event, locations) in creates.items():
            objects[obj_id] = ObjectLifecycle(
                obj_id=obj_id,
                type_name=create_event.type_name,
                created=create_event,
                destroyed=None,  # still alive
                locations=tuple(locations),
            )

        # Merge completed lifecycles (may overwrite if same id reused)
        objects.update(completed)

        return ObjectFlow(objects=objects, orphan_destroys=tuple(orphan_destroys))

    def analyze(
        self,
        result: TrackingResult,
        config: FilterConfig,
    ) -> AnalysisResult:
        """Full analysis pipeline: filter → build graphs.

        Pipeline:
            1. filter(result, config) → filtered TrackingResult
            2. build_call_graph(filtered) → CallGraph
            3. build_object_flow(filtered) → ObjectFlow
            4. Combine into AnalysisResult

        Args:
            result: Raw tracking result.
            config: Filter configuration.

        Returns:
            AnalysisResult with filtered result, call graph, and object flow.
        """
        filtered = self.filter(result, config)
        call_graph = self.build_call_graph(filtered)
        object_flow = self.build_object_flow(filtered)

        return AnalysisResult(
            filtered=filtered,
            call_graph=call_graph,
            object_flow=object_flow,
        )
