"""Merger service: merge static and runtime call graphs.

Combines AST analysis with runtime tracking.
Requires Codebase for Location → FQN resolution.

Phase 3 basic: STATIC_ONLY, RUNTIME_ONLY, BOTH.
PARAMETRIC detection deferred to Phase 4 (requires type analysis).
"""

from pathlib import Path
from typing import TYPE_CHECKING

from archcheck.domain.merged_graph import EdgeNature, MergedCallEdge, MergedCallGraph

if TYPE_CHECKING:
    from archcheck.domain.codebase import Codebase
    from archcheck.domain.events import Location
    from archcheck.domain.graphs import CallGraph
    from archcheck.domain.static_graph import StaticCallEdge, StaticCallGraph


def merge(
    static: StaticCallGraph,
    runtime: CallGraph,
    codebase: Codebase,
) -> MergedCallGraph:
    """Merge static and runtime call graphs.

    Algorithm:
        1. Build static index: (caller_fqn, callee_fqn) → StaticCallEdge
        2. Build function index from codebase: (file, func, line) → FQN
        3. For each runtime edge: resolve to FQN and classify
        4. Build MergedCallGraph

    EdgeNature classification:
        - BOTH: edge in static AND runtime
        - STATIC_ONLY: edge in static only
        - RUNTIME_ONLY: edge in runtime only (Phase 4 may refine to PARAMETRIC)

    Unresolved runtime edges (Location without file/func) are skipped.
    Phase 4 will add tracking for unresolved.

    Args:
        static: Static call graph from AST analysis.
        runtime: Runtime call graph from tracking.
        codebase: Parsed codebase for Location → FQN resolution.

    Returns:
        MergedCallGraph with classified edges.
    """
    # Step 1: Index static edges by (caller, callee)
    static_index: dict[tuple[str, str], StaticCallEdge] = {
        (edge.caller_fqn, edge.callee_fqn): edge for edge in static.edges
    }
    matched_static: set[tuple[str, str]] = set()

    # Step 2: Build function index from codebase
    func_index = _build_func_index(codebase)

    # Step 3: Process runtime edges
    merged_edges: list[MergedCallEdge] = []

    for runtime_edge in runtime.edges:
        caller_fqn = _resolve_location(runtime_edge.caller, func_index)
        callee_fqn = _resolve_location(runtime_edge.callee, func_index)

        if caller_fqn is None or callee_fqn is None:
            # Cannot resolve → skip (Phase 4 will track)
            continue

        key = (caller_fqn, callee_fqn)
        static_edge = static_index.get(key)

        if static_edge is not None:
            # Edge in both static and runtime → BOTH
            matched_static.add(key)
            merged_edges.append(
                MergedCallEdge(
                    caller_fqn=caller_fqn,
                    callee_fqn=callee_fqn,
                    static=static_edge,
                    runtime=runtime_edge,
                    nature=EdgeNature.BOTH,
                ),
            )
        else:
            # Edge only in runtime → RUNTIME_ONLY (Phase 4 may refine to PARAMETRIC)
            merged_edges.append(
                MergedCallEdge(
                    caller_fqn=caller_fqn,
                    callee_fqn=callee_fqn,
                    static=None,
                    runtime=runtime_edge,
                    nature=EdgeNature.RUNTIME_ONLY,
                ),
            )

    # Step 4: Add unmatched static edges → STATIC_ONLY
    for key, static_edge in static_index.items():
        if key not in matched_static:
            caller_fqn, callee_fqn = key
            merged_edges.append(
                MergedCallEdge(
                    caller_fqn=caller_fqn,
                    callee_fqn=callee_fqn,
                    static=static_edge,
                    runtime=None,
                    nature=EdgeNature.STATIC_ONLY,
                ),
            )

    return MergedCallGraph(edges=tuple(merged_edges))


def _build_func_index(codebase: Codebase) -> dict[tuple[str, str, int], str]:
    """Build index from (file, func_name, line) → FQN.

    Enables O(1) lookup for Location → FQN resolution.
    Uses resolved absolute paths for reliable matching.

    Args:
        codebase: Parsed codebase with modules.

    Returns:
        Index mapping (resolved_file_path, func_name, line) to qualified_name.
    """
    index: dict[tuple[str, str, int], str] = {}

    for module in codebase.modules.values():
        file_key = str(module.path.resolve())

        # Index top-level functions
        for func in module.functions:
            key = (file_key, func.name, func.location.line)
            index[key] = func.qualified_name

        # Index class methods (two keys: method_name and Class.method_name)
        for cls in module.classes:
            for method in cls.methods:
                # Key 1: method name only (for some trackers)
                key = (file_key, method.name, method.location.line)
                index[key] = method.qualified_name
                # Key 2: Class.method (Python runtime format)
                key_with_class = (file_key, f"{cls.name}.{method.name}", method.location.line)
                index[key_with_class] = method.qualified_name

    return index


def _resolve_location(
    location: Location,
    func_index: dict[tuple[str, str, int], str],
) -> str | None:
    """Resolve runtime Location to FQN.

    Returns None if:
        - location.file is None
        - location.func is None
        - Location not found in index

    Args:
        location: Runtime location (file, line, func).
        func_index: Prebuilt index from _build_func_index.

    Returns:
        Qualified function name or None if unresolvable.
    """
    if location.file is None or location.func is None:
        return None

    # Resolve path for consistent matching
    try:
        resolved_file = str(Path(location.file).resolve())
    except (OSError, ValueError):
        # Invalid path → cannot resolve
        return None

    key = (resolved_file, location.func, location.line)
    return func_index.get(key)
