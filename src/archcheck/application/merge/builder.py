"""Merged call graph builder combining AST and Runtime analysis."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from archcheck.domain.model.call_instance import CallInstance
from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.edge_nature import EdgeNature
from archcheck.domain.model.entry_points import EntryPointCategories
from archcheck.domain.model.function_edge import FunctionEdge
from archcheck.domain.model.hidden_dep import HiddenDep, HiddenDepType
from archcheck.domain.model.lib_edge import LibEdge
from archcheck.domain.model.location import Location
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from archcheck.infrastructure.analysis.edge_classifier import EdgeClassifier

if TYPE_CHECKING:
    from collections.abc import Mapping

    from archcheck.domain.model.call_site import CallSite
    from archcheck.domain.model.codebase import Codebase
    from archcheck.domain.model.function import Function
    from archcheck.domain.model.lib_call_site import LibCallSite
    from archcheck.domain.model.runtime_call_graph import FrozenRuntimeCallGraph
    from archcheck.domain.model.static_call_graph import StaticCallGraph


def build_merged_graph(
    static: StaticCallGraph,
    runtime: FrozenRuntimeCallGraph,
    module_imports: Mapping[str, frozenset[str]],
    known_frameworks: frozenset[str],
    entry_patterns: Mapping[str, tuple[str, ...]] | None = None,
) -> MergedCallGraph:
    """Build merged call graph combining AST and Runtime analysis.

    Algorithm:
    1. Aggregate runtime edges by (caller_fqn, callee_fqn)
    2. For each pair: classify EdgeNature, build CallInstances
    3. Build FunctionEdge for each pair
    4. Detect hidden deps (DYNAMIC only - PARAMETRIC/FRAMEWORK go to edges)
    5. Build LibEdges
    6. Categorize entry points

    Args:
        static: StaticCallGraph from AST analysis
        runtime: FrozenRuntimeCallGraph from sys.monitoring
        module_imports: Mapping from module FQN to imported modules (from Codebase)
        known_frameworks: Framework package prefixes (from config)
        entry_patterns: Optional patterns for entry point categorization

    Returns:
        MergedCallGraph with indexed FunctionEdges

    Raises:
        TypeError: If static, runtime, module_imports, or known_frameworks is None
    """
    # FAIL-FIRST validation
    if static is None:
        raise TypeError("static must not be None")
    if runtime is None:
        raise TypeError("runtime must not be None")
    if module_imports is None:
        raise TypeError("module_imports must not be None")
    if known_frameworks is None:
        raise TypeError("known_frameworks must not be None")

    # Build classifier
    classifier = EdgeClassifier(module_imports, known_frameworks)

    # Build set of AST edge pairs for O(1) lookup
    ast_pairs: set[tuple[str, str]] = {(edge.caller_fqn, edge.callee_fqn) for edge in static.edges}

    # Build AST edge lookup for call_type
    ast_edge_lookup: dict[tuple[str, str], CallType] = {
        (edge.caller_fqn, edge.callee_fqn): edge.call_type for edge in static.edges
    }

    # Step 1: Aggregate runtime edges by (caller_fqn, callee_fqn)
    aggregated: dict[tuple[str, str], list[tuple[CallSite, CallSite, int]]] = {}
    for (caller_site, callee_site), count in runtime.edges.items():
        key = (caller_site.fqn, callee_site.fqn)
        aggregated.setdefault(key, []).append((caller_site, callee_site, count))

    # Step 2-3: Build FunctionEdges and detect hidden deps
    edges: list[FunctionEdge] = []
    hidden_deps: set[HiddenDep] = set()

    for (caller_fqn, callee_fqn), call_list in aggregated.items():
        # Skip self-loops
        if caller_fqn == callee_fqn:
            continue

        # Get call_type from AST if available
        fqn_pair = (caller_fqn, callee_fqn)
        call_type = ast_edge_lookup.get(fqn_pair, CallType.FUNCTION)

        # Classify edge nature
        nature = classifier.classify(caller_fqn, callee_fqn, call_type)

        # Build CallInstances
        calls = tuple(
            CallInstance(
                location=Location(
                    file=caller_site.file,
                    line=caller_site.line,
                    column=0,
                ),
                call_type=call_type,
                count=count,
            )
            for caller_site, _callee_site, count in call_list
        )

        # Check if AST knows about this edge
        if fqn_pair in ast_pairs:
            # Known edge → FunctionEdge
            edges.append(
                FunctionEdge(
                    caller_fqn=caller_fqn,
                    callee_fqn=callee_fqn,
                    nature=nature,
                    calls=calls,
                )
            )
        else:
            # Runtime-only edge
            # PARAMETRIC and FRAMEWORK are valid patterns → go to edges
            # DIRECT without AST edge is suspicious but possible (dynamic import)
            # Only truly DYNAMIC (no pattern match) goes to hidden_deps
            if nature in (EdgeNature.PARAMETRIC, EdgeNature.FRAMEWORK, EdgeNature.INHERITED):
                edges.append(
                    FunctionEdge(
                        caller_fqn=caller_fqn,
                        callee_fqn=callee_fqn,
                        nature=nature,
                        calls=calls,
                    )
                )
            else:
                # DIRECT but not in AST → true hidden dependency (dynamic dispatch)
                hidden_deps.add(
                    HiddenDep(
                        caller_fqn=caller_fqn,
                        callee_fqn=callee_fqn,
                        dep_type=HiddenDepType.DYNAMIC,
                    )
                )

    # Step 4: Build LibEdges
    lib_edges = _build_lib_edges(runtime)

    # Step 5: Collect nodes (all FQNs from runtime)
    nodes = {site.fqn for site in runtime.called_functions}

    # Step 6: Categorize entry points
    entry_points = _categorize_entry_points(nodes, entry_patterns)

    return MergedCallGraph.build(
        nodes=frozenset(nodes),
        edges=edges,
        lib_edges=lib_edges,
        hidden_deps=hidden_deps,
        entry_points=entry_points,
    )


def _build_lib_edges(runtime: FrozenRuntimeCallGraph) -> list[LibEdge]:
    """Build library edges from runtime.

    Aggregates by (caller_fqn, lib_fqn) and builds LibEdge objects.

    Args:
        runtime: FrozenRuntimeCallGraph from sys.monitoring

    Returns:
        List of LibEdge objects
    """
    # Aggregate by (caller_fqn, lib_fqn)
    aggregated: dict[tuple[str, str], list[tuple[CallSite, LibCallSite, int]]] = {}

    for (caller_site, lib_site), count in runtime.lib_edges.items():
        key = (caller_site.fqn, lib_site.fqn)
        aggregated.setdefault(key, []).append((caller_site, lib_site, count))

    lib_edges: list[LibEdge] = []

    for (caller_fqn, _lib_fqn), call_list in aggregated.items():
        # Get lib_target from first call (all have same lib_site for this key)
        lib_target = call_list[0][1]

        # Build CallInstances
        calls = tuple(
            CallInstance(
                location=Location(
                    file=caller_site.file,
                    line=caller_site.line,
                    column=0,
                ),
                call_type=CallType.FUNCTION,  # Library calls are typically function calls
                count=count,
            )
            for caller_site, _lib_site, count in call_list
        )

        lib_edges.append(
            LibEdge(
                caller_fqn=caller_fqn,
                lib_target=lib_target,
                calls=calls,
            )
        )

    return lib_edges


def _categorize_entry_points(
    runtime_fqns: set[str],
    entry_patterns: Mapping[str, tuple[str, ...]] | None,
) -> EntryPointCategories:
    """Categorize entry points by patterns.

    Entry points are functions that appear in runtime but have no callers
    (roots of the call tree).

    Args:
        runtime_fqns: All FQNs from runtime
        entry_patterns: Optional patterns for categorization

    Returns:
        EntryPointCategories with categorized entry points
    """
    # TODO: Implement entry point categorization based on patterns
    # For now, return empty categories
    return EntryPointCategories.empty()


def build_static_merged_graph(
    codebase: Codebase,
    known_frameworks: frozenset[str] | None = None,
) -> MergedCallGraph:
    """Build MergedCallGraph from static analysis only.

    Creates FunctionEdges from Codebase without runtime data.
    Use for static-only architecture testing.

    Args:
        codebase: Parsed codebase
        known_frameworks: Framework prefixes for EdgeClassifier

    Returns:
        MergedCallGraph with static edges

    Raises:
        TypeError: If codebase is None
    """
    if codebase is None:
        raise TypeError("codebase must not be None")

    frameworks = known_frameworks or frozenset()
    module_imports = _extract_module_imports(codebase)
    classifier = EdgeClassifier(module_imports, frameworks)

    # Collect: (caller_fqn, callee_fqn) → [(file, line, call_type), ...]
    edge_data: dict[tuple[str, str], list[tuple[Path, int, CallType]]] = {}
    all_functions: set[str] = set()

    for module in codebase.modules.values():
        for func in module.functions:
            _collect_static_edges(func, edge_data, all_functions)
        for cls in module.classes:
            for method in cls.methods:
                _collect_static_edges(method, edge_data, all_functions)

    # Build FunctionEdges
    edges: list[FunctionEdge] = []
    for (caller_fqn, callee_fqn), call_list in edge_data.items():
        if caller_fqn == callee_fqn:
            continue  # Skip self-loops

        call_type = call_list[0][2]
        nature = classifier.classify(caller_fqn, callee_fqn, call_type)

        calls = tuple(
            CallInstance(
                location=Location(file=file, line=line, column=0),
                call_type=ct,
                count=1,
            )
            for file, line, ct in call_list
        )

        edges.append(
            FunctionEdge(
                caller_fqn=caller_fqn,
                callee_fqn=callee_fqn,
                nature=nature,
                calls=calls,
            )
        )

    nodes = all_functions | {e.callee_fqn for e in edges}

    return MergedCallGraph.build(
        nodes=frozenset(nodes),
        edges=edges,
        lib_edges=[],
        hidden_deps=[],
        entry_points=EntryPointCategories.empty(),
    )


def _collect_static_edges(
    func: Function,
    edge_data: dict[tuple[str, str], list[tuple[Path, int, CallType]]],
    all_functions: set[str],
) -> None:
    """Collect edges from function body_calls."""
    all_functions.add(func.qualified_name)
    for call in func.body_calls:
        if call.is_resolved and call.resolved_fqn is not None:
            key = (func.qualified_name, call.resolved_fqn)
            edge_data.setdefault(key, []).append((func.location.file, call.line, call.call_type))


def _extract_module_imports(codebase: Codebase) -> Mapping[str, frozenset[str]]:
    """Extract module imports for EdgeClassifier."""
    result: dict[str, frozenset[str]] = {}
    for name, module in codebase.modules.items():
        result[name] = frozenset(imp.module for imp in module.imports)
    return MappingProxyType(result)
