"""Test factories for creating domain objects.

Centralized factory functions to avoid duplication across test modules.
All factories follow the same pattern: accept simplified parameters,
return fully constructed domain objects.
"""

from pathlib import Path
from types import MappingProxyType

from archcheck.domain.model.call_instance import CallInstance
from archcheck.domain.model.call_site import CallSite
from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.edge_nature import EdgeNature
from archcheck.domain.model.entry_points import EntryPointCategories
from archcheck.domain.model.function_edge import FunctionEdge
from archcheck.domain.model.lib_call_site import LibCallSite
from archcheck.domain.model.location import Location
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from archcheck.domain.model.runtime_call_graph import FrozenRuntimeCallGraph
from archcheck.domain.model.static_call_edge import StaticCallEdge
from archcheck.domain.model.static_call_graph import StaticCallGraph

# Default test file path - consistent across all tests
DEFAULT_TEST_FILE = Path("/test/file.py")


def make_call_site(
    module: str,
    function: str,
    line: int = 1,
    file: Path = DEFAULT_TEST_FILE,
) -> CallSite:
    """Create a CallSite for tests.

    Args:
        module: Module name
        function: Function name
        line: Line number (default 1)
        file: File path (default test file)

    Returns:
        CallSite instance
    """
    return CallSite(module=module, function=function, line=line, file=file)


def fqn_to_call_site(fqn: str, line: int = 1, file: Path = DEFAULT_TEST_FILE) -> CallSite:
    """Convert FQN string to CallSite.

    Parses FQN like "myapp.module.function" into module="myapp.module", function="function".

    Args:
        fqn: Fully qualified name
        line: Line number (default 1)
        file: File path (default test file)

    Returns:
        CallSite instance
    """
    parts = fqn.rsplit(".", 1)
    if len(parts) == 2:
        module, function = parts
    else:
        module, function = fqn, fqn
    return CallSite(module=module, function=function, line=line, file=file)


def make_lib_call_site(lib_name: str, function: str) -> LibCallSite:
    """Create a LibCallSite for tests.

    Args:
        lib_name: Library name
        function: Function name

    Returns:
        LibCallSite instance
    """
    return LibCallSite(lib_name=lib_name, function=function)


def make_static_edge(
    caller_fqn: str,
    callee_fqn: str,
    line: int = 1,
    call_type: CallType = CallType.FUNCTION,
) -> StaticCallEdge:
    """Create a StaticCallEdge for tests.

    Args:
        caller_fqn: Caller FQN
        callee_fqn: Callee FQN
        line: Line number (default 1)
        call_type: Call type (default FUNCTION)

    Returns:
        StaticCallEdge instance
    """
    return StaticCallEdge(
        caller_fqn=caller_fqn,
        callee_fqn=callee_fqn,
        line=line,
        call_type=call_type,
    )


def make_static_graph(
    edges: frozenset[StaticCallEdge] | None = None,
    functions: frozenset[str] | None = None,
    decorators: frozenset[str] | None = None,
) -> StaticCallGraph:
    """Create a StaticCallGraph for tests.

    Args:
        edges: Static call edges (default empty)
        functions: Function FQNs (auto-populated from edges if None)
        decorators: Decorator FQNs (default empty)

    Returns:
        StaticCallGraph instance
    """
    edges = edges or frozenset()
    decorators = decorators or frozenset()

    # Auto-populate functions from edges
    if functions is None:
        functions = frozenset(edge.caller_fqn for edge in edges)

    return StaticCallGraph(
        edges=edges,
        functions=functions,
        decorators=decorators,
    )


def make_runtime_graph(
    edges: dict[tuple[CallSite, CallSite], int] | None = None,
    lib_edges: dict[tuple[CallSite, LibCallSite], int] | None = None,
    called_functions: frozenset[CallSite] | None = None,
) -> FrozenRuntimeCallGraph:
    """Create a FrozenRuntimeCallGraph for tests.

    Args:
        edges: App→App edges (default empty)
        lib_edges: App→Lib edges (default empty)
        called_functions: Called functions (auto-populated from edges if None)

    Returns:
        FrozenRuntimeCallGraph instance
    """
    edges = edges or {}
    lib_edges = lib_edges or {}

    # Auto-populate called_functions from edges
    if called_functions is None:
        called_functions = frozenset(callee for _, callee in edges)

    return FrozenRuntimeCallGraph(
        edges=MappingProxyType(edges),
        lib_edges=MappingProxyType(lib_edges),
        called_functions=called_functions,
    )


def make_call_instance(
    line: int = 1,
    file: Path = DEFAULT_TEST_FILE,
    call_type: CallType = CallType.FUNCTION,
    count: int = 1,
) -> CallInstance:
    """Create a CallInstance for tests.

    Args:
        line: Line number (default 1)
        file: File path (default test file)
        call_type: Call type (default FUNCTION)
        count: Call count (default 1)

    Returns:
        CallInstance instance
    """
    return CallInstance(
        location=Location(file=file, line=line, column=0),
        call_type=call_type,
        count=count,
    )


def make_function_edge(
    caller_fqn: str,
    callee_fqn: str,
    nature: EdgeNature = EdgeNature.DIRECT,
    count: int = 1,
    line: int = 1,
    file: Path = DEFAULT_TEST_FILE,
) -> FunctionEdge:
    """Create a FunctionEdge for tests.

    Args:
        caller_fqn: Caller FQN
        callee_fqn: Callee FQN
        nature: Edge nature (default DIRECT)
        count: Call count (default 1)
        line: Line number (default 1)
        file: File path (default test file)

    Returns:
        FunctionEdge instance
    """
    return FunctionEdge(
        caller_fqn=caller_fqn,
        callee_fqn=callee_fqn,
        nature=nature,
        calls=(make_call_instance(line=line, file=file, count=count),),
    )


def make_merged_graph(
    internal_edges: dict[tuple[str, str], int] | None = None,
    nodes: frozenset[str] | None = None,
    nature: EdgeNature = EdgeNature.DIRECT,
) -> MergedCallGraph:
    """Create a MergedCallGraph for tests.

    Accepts FQN strings for convenience and converts to FunctionEdge internally.

    Args:
        internal_edges: Dict of (caller_fqn, callee_fqn) -> count
        nodes: Set of all node FQNs (auto-populated from edges if None)
        nature: Edge nature for all edges (default DIRECT)

    Returns:
        MergedCallGraph instance
    """
    internal_edges = internal_edges or {}

    # Auto-populate nodes from edges
    if nodes is None:
        nodes_set: set[str] = set()
        for caller, callee in internal_edges:
            nodes_set.add(caller)
            nodes_set.add(callee)
        nodes = frozenset(nodes_set)

    # Convert (str, str) edges to FunctionEdge
    function_edges: list[FunctionEdge] = []
    for (caller_fqn, callee_fqn), count in internal_edges.items():
        function_edges.append(
            make_function_edge(
                caller_fqn=caller_fqn,
                callee_fqn=callee_fqn,
                nature=nature,
                count=count,
            )
        )

    return MergedCallGraph(
        nodes=nodes,
        edges=tuple(function_edges),
        lib_edges=(),
        hidden_deps=frozenset(),
        entry_points=EntryPointCategories.empty(),
    )
