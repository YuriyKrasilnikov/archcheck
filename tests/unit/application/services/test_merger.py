"""Tests for merger service.

Tests:
- merge: empty graphs, static only, runtime only, both
- _build_func_index: top-level functions, methods
- _resolve_location: valid, invalid (None file/func)
- EdgeNature classification: STATIC_ONLY, RUNTIME_ONLY, BOTH
"""

from typing import TYPE_CHECKING

from archcheck.application.services.merger import (
    _build_func_index,
    _resolve_location,
    merge,
)
from archcheck.domain.codebase import Class, Codebase, Function, Module
from archcheck.domain.events import Location
from archcheck.domain.graphs import CallEdge, CallGraph
from archcheck.domain.merged_graph import EdgeNature
from archcheck.domain.static_graph import CallType, StaticCallEdge, StaticCallGraph

if TYPE_CHECKING:
    from pathlib import Path


def _make_location(
    file: str | None = None,
    line: int = 1,
    func: str | None = None,
) -> Location:
    """Create test location."""
    return Location(file=file, line=line, func=func)


def _make_function(
    name: str,
    module_name: str,
    *,
    class_name: str | None = None,
    line: int = 1,
) -> Function:
    """Create test function."""
    qualified_name = f"{module_name}.{class_name}.{name}" if class_name else f"{module_name}.{name}"

    return Function(
        name=name,
        qualified_name=qualified_name,
        parameters=(),
        return_annotation=None,
        location=_make_location(line=line),
        is_async=False,
        is_generator=False,
        is_method=class_name is not None,
        decorators=(),
        body_calls=(),
    )


def _make_class(
    name: str,
    module_name: str,
    *,
    methods: tuple[Function, ...] = (),
) -> Class:
    """Create test class."""
    return Class(
        name=name,
        qualified_name=f"{module_name}.{name}",
        bases=(),
        methods=methods,
        location=_make_location(),
        is_protocol=False,
        is_dataclass=False,
    )


def _make_module(
    name: str,
    path: Path,
    *,
    functions: tuple[Function, ...] = (),
    classes: tuple[Class, ...] = (),
) -> Module:
    """Create test module."""
    return Module(
        name=name,
        path=path,
        imports=(),
        classes=classes,
        functions=functions,
        docstring=None,
    )


def _make_static_edge(
    caller: str,
    callee: str,
    *,
    call_type: CallType = CallType.DIRECT,
) -> StaticCallEdge:
    """Create test static edge."""
    return StaticCallEdge(
        caller_fqn=caller,
        callee_fqn=callee,
        location=_make_location(),
        call_type=call_type,
    )


def _make_call_edge(
    caller_file: str,
    caller_func: str,
    caller_line: int,
    callee_file: str,
    callee_func: str,
    callee_line: int,
) -> CallEdge:
    """Create test runtime edge."""
    return CallEdge(
        caller=_make_location(file=caller_file, func=caller_func, line=caller_line),
        callee=_make_location(file=callee_file, func=callee_func, line=callee_line),
        count=1,
    )


class TestMergeEmpty:
    """Tests for merge with empty graphs."""

    def test_empty_both(self, tmp_path: Path) -> None:
        """Empty static + empty runtime → empty merged."""
        codebase = Codebase.empty()
        static = StaticCallGraph.empty()
        runtime = CallGraph(edges=frozenset(), unmatched=())

        result = merge(static, runtime, codebase)

        assert result.edges == ()
        assert result.nodes == frozenset()

    def test_empty_runtime(self, tmp_path: Path) -> None:
        """Static edges only → all STATIC_ONLY."""
        file = tmp_path / "app" / "main.py"
        file.parent.mkdir(parents=True)
        file.touch()

        func_foo = _make_function("foo", "app.main", line=1)
        func_bar = _make_function("bar", "app.main", line=5)
        module = _make_module("app.main", file, functions=(func_foo, func_bar))

        codebase = Codebase(
            root_path=tmp_path,
            root_package="app",
            modules={"app.main": module},
        )
        static = StaticCallGraph(
            edges=(_make_static_edge("app.main.foo", "app.main.bar"),),
            unresolved=(),
        )
        runtime = CallGraph(edges=frozenset(), unmatched=())

        result = merge(static, runtime, codebase)

        assert len(result.edges) == 1
        assert result.edges[0].nature == EdgeNature.STATIC_ONLY
        assert result.edges[0].caller_fqn == "app.main.foo"
        assert result.edges[0].callee_fqn == "app.main.bar"
        assert result.edges[0].static is not None
        assert result.edges[0].runtime is None


class TestMergeRuntimeOnly:
    """Tests for merge with runtime-only edges."""

    def test_runtime_only_resolved(self, tmp_path: Path) -> None:
        """Runtime edge resolved → RUNTIME_ONLY."""
        file = tmp_path / "app" / "main.py"
        file.parent.mkdir(parents=True)
        file.touch()

        func_foo = _make_function("foo", "app.main", line=1)
        func_bar = _make_function("bar", "app.main", line=5)
        module = _make_module("app.main", file, functions=(func_foo, func_bar))

        codebase = Codebase(
            root_path=tmp_path,
            root_package="app",
            modules={"app.main": module},
        )
        static = StaticCallGraph.empty()
        runtime_edge = _make_call_edge(
            caller_file=str(file),
            caller_func="foo",
            caller_line=1,
            callee_file=str(file),
            callee_func="bar",
            callee_line=5,
        )
        runtime = CallGraph(edges=frozenset({runtime_edge}), unmatched=())

        result = merge(static, runtime, codebase)

        assert len(result.edges) == 1
        assert result.edges[0].nature == EdgeNature.RUNTIME_ONLY
        assert result.edges[0].caller_fqn == "app.main.foo"
        assert result.edges[0].callee_fqn == "app.main.bar"
        assert result.edges[0].static is None
        assert result.edges[0].runtime is not None

    def test_runtime_unresolved_caller_skipped(self, tmp_path: Path) -> None:
        """Runtime edge with None caller file → skipped."""
        file = tmp_path / "main.py"
        file.touch()

        func = _make_function("bar", "main", line=5)
        module = _make_module("main", file, functions=(func,))
        codebase = Codebase(
            root_path=tmp_path,
            root_package="main",
            modules={"main": module},
        )
        runtime_edge = _make_call_edge(
            caller_file=None,  # type: ignore[arg-type]
            caller_func="unknown",
            caller_line=1,
            callee_file=str(file),
            callee_func="bar",
            callee_line=5,
        )
        runtime = CallGraph(edges=frozenset({runtime_edge}), unmatched=())

        result = merge(StaticCallGraph.empty(), runtime, codebase)

        assert result.edges == ()

    def test_runtime_unresolved_callee_skipped(self, tmp_path: Path) -> None:
        """Runtime edge with None callee func → skipped."""
        file = tmp_path / "main.py"
        file.touch()

        func = _make_function("foo", "main", line=1)
        module = _make_module("main", file, functions=(func,))
        codebase = Codebase(
            root_path=tmp_path,
            root_package="main",
            modules={"main": module},
        )
        runtime_edge = _make_call_edge(
            caller_file=str(file),
            caller_func="foo",
            caller_line=1,
            callee_file=str(file),
            callee_func=None,  # type: ignore[arg-type]
            callee_line=5,
        )
        runtime = CallGraph(edges=frozenset({runtime_edge}), unmatched=())

        result = merge(StaticCallGraph.empty(), runtime, codebase)

        assert result.edges == ()


class TestMergeBoth:
    """Tests for merge with both static and runtime."""

    def test_matching_edges_become_both(self, tmp_path: Path) -> None:
        """Edge in static AND runtime → BOTH."""
        file = tmp_path / "app" / "main.py"
        file.parent.mkdir(parents=True)
        file.touch()

        func_foo = _make_function("foo", "app.main", line=1)
        func_bar = _make_function("bar", "app.main", line=5)
        module = _make_module("app.main", file, functions=(func_foo, func_bar))

        codebase = Codebase(
            root_path=tmp_path,
            root_package="app",
            modules={"app.main": module},
        )
        static = StaticCallGraph(
            edges=(_make_static_edge("app.main.foo", "app.main.bar"),),
            unresolved=(),
        )
        runtime_edge = _make_call_edge(
            caller_file=str(file),
            caller_func="foo",
            caller_line=1,
            callee_file=str(file),
            callee_func="bar",
            callee_line=5,
        )
        runtime = CallGraph(edges=frozenset({runtime_edge}), unmatched=())

        result = merge(static, runtime, codebase)

        assert len(result.edges) == 1
        assert result.edges[0].nature == EdgeNature.BOTH
        assert result.edges[0].static is not None
        assert result.edges[0].runtime is not None

    def test_mixed_natures(self, tmp_path: Path) -> None:
        """Mix of STATIC_ONLY, RUNTIME_ONLY, BOTH."""
        file = tmp_path / "main.py"
        file.touch()

        func_a = _make_function("a", "main", line=1)
        func_b = _make_function("b", "main", line=5)
        func_c = _make_function("c", "main", line=10)
        func_d = _make_function("d", "main", line=15)
        module = _make_module("main", file, functions=(func_a, func_b, func_c, func_d))

        codebase = Codebase(
            root_path=tmp_path,
            root_package="main",
            modules={"main": module},
        )
        # Static: a→b, b→c
        static = StaticCallGraph(
            edges=(
                _make_static_edge("main.a", "main.b"),
                _make_static_edge("main.b", "main.c"),
            ),
            unresolved=(),
        )
        # Runtime: a→b (matches), c→d (runtime only)
        runtime = CallGraph(
            edges=frozenset(
                {
                    _make_call_edge(str(file), "a", 1, str(file), "b", 5),
                    _make_call_edge(str(file), "c", 10, str(file), "d", 15),
                },
            ),
            unmatched=(),
        )

        result = merge(static, runtime, codebase)

        by_nature = result.by_nature
        assert EdgeNature.BOTH in by_nature
        assert EdgeNature.STATIC_ONLY in by_nature
        assert EdgeNature.RUNTIME_ONLY in by_nature

        # a→b is BOTH
        both_edges = by_nature[EdgeNature.BOTH]
        assert len(both_edges) == 1
        assert both_edges[0].caller_fqn == "main.a"
        assert both_edges[0].callee_fqn == "main.b"

        # b→c is STATIC_ONLY
        static_only = by_nature[EdgeNature.STATIC_ONLY]
        assert len(static_only) == 1
        assert static_only[0].caller_fqn == "main.b"

        # c→d is RUNTIME_ONLY
        runtime_only = by_nature[EdgeNature.RUNTIME_ONLY]
        assert len(runtime_only) == 1
        assert runtime_only[0].caller_fqn == "main.c"


class TestBuildFuncIndex:
    """Tests for _build_func_index."""

    def test_indexes_top_level_functions(self, tmp_path: Path) -> None:
        """Top-level functions indexed by (file, name, line)."""
        file = tmp_path / "main.py"
        file.touch()

        func = _make_function("foo", "main", line=10)
        module = _make_module("main", file, functions=(func,))
        codebase = Codebase(
            root_path=tmp_path,
            root_package="main",
            modules={"main": module},
        )

        index = _build_func_index(codebase)

        key = (str(file.resolve()), "foo", 10)
        assert key in index
        assert index[key] == "main.foo"

    def test_indexes_class_methods(self, tmp_path: Path) -> None:
        """Class methods indexed by (file, method_name, line)."""
        file = tmp_path / "service.py"
        file.touch()

        method = _make_function("process", "service", class_name="Service", line=5)
        cls = _make_class("Service", "service", methods=(method,))
        module = _make_module("service", file, classes=(cls,))
        codebase = Codebase(
            root_path=tmp_path,
            root_package="service",
            modules={"service": module},
        )

        index = _build_func_index(codebase)

        # Key 1: method name only
        key = (str(file.resolve()), "process", 5)
        assert key in index
        assert index[key] == "service.Service.process"

    def test_indexes_class_methods_with_class_prefix(self, tmp_path: Path) -> None:
        """Class methods also indexed by (file, Class.method, line) for Python runtime."""
        file = tmp_path / "service.py"
        file.touch()

        method = _make_function("process", "service", class_name="Service", line=5)
        cls = _make_class("Service", "service", methods=(method,))
        module = _make_module("service", file, classes=(cls,))
        codebase = Codebase(
            root_path=tmp_path,
            root_package="service",
            modules={"service": module},
        )

        index = _build_func_index(codebase)

        # Key 2: Class.method (Python runtime format)
        key_with_class = (str(file.resolve()), "Service.process", 5)
        assert key_with_class in index
        assert index[key_with_class] == "service.Service.process"

    def test_empty_codebase(self) -> None:
        """Empty codebase → empty index."""
        codebase = Codebase.empty()
        index = _build_func_index(codebase)
        assert index == {}


class TestResolveLocation:
    """Tests for _resolve_location."""

    def test_resolves_valid_location(self, tmp_path: Path) -> None:
        """Valid location → FQN."""
        file = tmp_path / "main.py"
        file.touch()

        index = {(str(file.resolve()), "foo", 10): "main.foo"}
        location = _make_location(file=str(file), line=10, func="foo")

        result = _resolve_location(location, index)

        assert result == "main.foo"

    def test_returns_none_for_missing_file(self) -> None:
        """Location with file=None → None."""
        location = _make_location(file=None, line=10, func="foo")
        result = _resolve_location(location, {})
        assert result is None

    def test_returns_none_for_missing_func(self, tmp_path: Path) -> None:
        """Location with func=None → None."""
        file = tmp_path / "main.py"
        location = _make_location(file=str(file), line=10, func=None)
        result = _resolve_location(location, {})
        assert result is None

    def test_returns_none_for_not_in_index(self, tmp_path: Path) -> None:
        """Location not in index → None."""
        file = tmp_path / "main.py"
        file.touch()

        location = _make_location(file=str(file), line=10, func="unknown")
        result = _resolve_location(location, {})
        assert result is None


class TestMergedGraphIndexes:
    """Tests for MergedCallGraph index population."""

    def test_nodes_populated(self, tmp_path: Path) -> None:
        """All callers and callees in nodes."""
        file = tmp_path / "main.py"
        file.touch()

        func_a = _make_function("a", "main", line=1)
        func_b = _make_function("b", "main", line=5)
        module = _make_module("main", file, functions=(func_a, func_b))

        codebase = Codebase(
            root_path=tmp_path,
            root_package="main",
            modules={"main": module},
        )
        static = StaticCallGraph(
            edges=(_make_static_edge("main.a", "main.b"),),
            unresolved=(),
        )

        result = merge(static, CallGraph(edges=frozenset(), unmatched=()), codebase)

        assert "main.a" in result.nodes
        assert "main.b" in result.nodes

    def test_by_caller_index(self, tmp_path: Path) -> None:
        """by_caller maps caller → callees."""
        file = tmp_path / "main.py"
        file.touch()

        func_a = _make_function("a", "main", line=1)
        func_b = _make_function("b", "main", line=5)
        func_c = _make_function("c", "main", line=10)
        module = _make_module("main", file, functions=(func_a, func_b, func_c))

        codebase = Codebase(
            root_path=tmp_path,
            root_package="main",
            modules={"main": module},
        )
        static = StaticCallGraph(
            edges=(
                _make_static_edge("main.a", "main.b"),
                _make_static_edge("main.a", "main.c"),
            ),
            unresolved=(),
        )

        result = merge(static, CallGraph(edges=frozenset(), unmatched=()), codebase)

        assert result.by_caller["main.a"] == frozenset({"main.b", "main.c"})

    def test_by_callee_index(self, tmp_path: Path) -> None:
        """by_callee maps callee → callers."""
        file = tmp_path / "main.py"
        file.touch()

        func_a = _make_function("a", "main", line=1)
        func_b = _make_function("b", "main", line=5)
        func_c = _make_function("c", "main", line=10)
        module = _make_module("main", file, functions=(func_a, func_b, func_c))

        codebase = Codebase(
            root_path=tmp_path,
            root_package="main",
            modules={"main": module},
        )
        static = StaticCallGraph(
            edges=(
                _make_static_edge("main.a", "main.c"),
                _make_static_edge("main.b", "main.c"),
            ),
            unresolved=(),
        )

        result = merge(static, CallGraph(edges=frozenset(), unmatched=()), codebase)

        assert result.by_callee["main.c"] == frozenset({"main.a", "main.b"})
