"""Tests for build_static_merged_graph in application/merge/builder.py."""

from pathlib import Path

import pytest

from archcheck.application.merge import build_static_merged_graph
from archcheck.domain.model.call_info import CallInfo
from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.class_ import Class
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.edge_nature import EdgeNature
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.import_ import Import
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module


def make_location(line: int = 1) -> Location:
    """Create a valid Location."""
    return Location(file=Path("test.py"), line=line, column=0)


def make_call_info(
    callee: str,
    resolved: str | None = None,
    line: int = 10,
    call_type: CallType = CallType.FUNCTION,
) -> CallInfo:
    """Create a valid CallInfo."""
    return CallInfo(
        callee_name=callee,
        resolved_fqn=resolved,
        line=line,
        call_type=call_type,
    )


def make_function(
    name: str,
    qualified_name: str,
    body_calls: tuple[CallInfo, ...] = (),
    file: Path | None = None,
) -> Function:
    """Create a valid Function."""
    return Function(
        name=name,
        qualified_name=qualified_name,
        parameters=(),
        return_annotation=None,
        decorators=(),
        location=Location(file=file or Path("test.py"), line=1, column=0),
        visibility=Visibility.PUBLIC,
        is_async=False,
        is_method=False,
        body_calls=body_calls,
    )


def make_import(module: str, line: int = 1) -> Import:
    """Create a valid Import."""
    return Import(
        module=module,
        name=None,
        alias=None,
        location=make_location(line),
    )


def make_module(
    name: str,
    functions: tuple[Function, ...] = (),
    imports: tuple[Import, ...] = (),
    classes: tuple[Class, ...] = (),
) -> Module:
    """Create a valid Module."""
    return Module(
        name=name,
        path=Path(f"{name.replace('.', '/')}.py"),
        imports=imports,
        classes=classes,
        functions=functions,
        constants=(),
    )


def make_codebase(*modules: Module, root_package: str = "myapp") -> Codebase:
    """Create a Codebase with given modules."""
    codebase = Codebase(root_path=Path("/test"), root_package=root_package)
    for module in modules:
        codebase.add_module(module)
    return codebase


class TestBuildStaticMergedGraphValidation:
    """Tests for validation in build_static_merged_graph."""

    def test_none_codebase_raises(self) -> None:
        """None codebase raises TypeError."""
        with pytest.raises(TypeError, match="codebase must not be None"):
            build_static_merged_graph(None)  # type: ignore[arg-type]

    def test_empty_codebase_returns_empty_graph(self) -> None:
        """Empty codebase returns empty graph."""
        codebase = make_codebase()
        graph = build_static_merged_graph(codebase)

        assert graph.node_count == 0
        assert graph.edge_count == 0


class TestBuildStaticMergedGraphEdges:
    """Tests for edge building."""

    def test_single_call_creates_edge(self) -> None:
        """Single resolved call creates one edge."""
        call = make_call_info("bar", "myapp.bar", line=10)
        foo = make_function("foo", "myapp.foo", body_calls=(call,))
        bar = make_function("bar", "myapp.bar")
        module = make_module("myapp", functions=(foo, bar))
        codebase = make_codebase(module)

        graph = build_static_merged_graph(codebase)

        assert graph.edge_count == 1
        edge = graph.edges[0]
        assert edge.caller_fqn == "myapp.foo"
        assert edge.callee_fqn == "myapp.bar"

    def test_unresolved_call_ignored(self) -> None:
        """Unresolved call doesn't create edge."""
        call = make_call_info("unknown", resolved=None)
        foo = make_function("foo", "myapp.foo", body_calls=(call,))
        module = make_module("myapp", functions=(foo,))
        codebase = make_codebase(module)

        graph = build_static_merged_graph(codebase)

        assert graph.edge_count == 0

    def test_self_loop_skipped(self) -> None:
        """Self-loop (function calls itself) skipped."""
        call = make_call_info("foo", "myapp.foo")
        foo = make_function("foo", "myapp.foo", body_calls=(call,))
        module = make_module("myapp", functions=(foo,))
        codebase = make_codebase(module)

        graph = build_static_merged_graph(codebase)

        assert graph.edge_count == 0

    def test_multiple_calls_aggregated(self) -> None:
        """Multiple calls to same function aggregated into one edge."""
        call1 = make_call_info("bar", "myapp.bar", line=10)
        call2 = make_call_info("bar", "myapp.bar", line=20)
        foo = make_function("foo", "myapp.foo", body_calls=(call1, call2))
        bar = make_function("bar", "myapp.bar")
        module = make_module("myapp", functions=(foo, bar))
        codebase = make_codebase(module)

        graph = build_static_merged_graph(codebase)

        assert graph.edge_count == 1
        edge = graph.edges[0]
        assert len(edge.calls) == 2


class TestBuildStaticMergedGraphNature:
    """Tests for edge nature classification."""

    def test_direct_call_has_direct_nature(self) -> None:
        """Direct call (with import) has DIRECT nature."""
        imp = make_import("myapp.infra")
        call = make_call_info("bar", "myapp.infra.bar")
        foo = make_function("foo", "myapp.domain.foo", body_calls=(call,))
        bar = make_function("bar", "myapp.infra.bar")
        m1 = make_module("myapp.domain", functions=(foo,), imports=(imp,))
        m2 = make_module("myapp.infra", functions=(bar,))
        codebase = make_codebase(m1, m2)

        graph = build_static_merged_graph(codebase)

        assert graph.edge_count == 1
        assert graph.edges[0].nature == EdgeNature.DIRECT

    def test_super_call_has_inherited_nature(self) -> None:
        """super() call has INHERITED nature."""
        call = make_call_info("super", "myapp.Base.__init__", call_type=CallType.SUPER)
        init = make_function("__init__", "myapp.Child.__init__", body_calls=(call,))
        base_init = make_function("__init__", "myapp.Base.__init__")
        m = make_module("myapp", functions=(init, base_init))
        codebase = make_codebase(m)

        graph = build_static_merged_graph(codebase)

        assert graph.edge_count == 1
        assert graph.edges[0].nature == EdgeNature.INHERITED


class TestBuildStaticMergedGraphNodes:
    """Tests for node collection."""

    def test_all_functions_in_nodes(self) -> None:
        """All functions from codebase in nodes."""
        foo = make_function("foo", "myapp.foo")
        bar = make_function("bar", "myapp.bar")
        module = make_module("myapp", functions=(foo, bar))
        codebase = make_codebase(module)

        graph = build_static_merged_graph(codebase)

        assert "myapp.foo" in graph.nodes
        assert "myapp.bar" in graph.nodes

    def test_external_callees_in_nodes(self) -> None:
        """External callees (from calls) added to nodes."""
        call = make_call_info("external", "external.lib.func")
        foo = make_function("foo", "myapp.foo", body_calls=(call,))
        module = make_module("myapp", functions=(foo,))
        codebase = make_codebase(module)

        graph = build_static_merged_graph(codebase)

        assert "myapp.foo" in graph.nodes
        assert "external.lib.func" in graph.nodes


class TestBuildStaticMergedGraphFrameworks:
    """Tests for framework classification."""

    def test_app_calling_framework_is_direct(self) -> None:
        """App calling framework has DIRECT nature (not FRAMEWORK).

        FRAMEWORK means framework calls app, not app calls framework.
        """
        imp = make_import("pytest")
        call = make_call_info("mark", "pytest.mark.skip")
        foo = make_function("test_foo", "myapp.tests.test_foo", body_calls=(call,))
        m = make_module("myapp.tests", functions=(foo,), imports=(imp,))
        codebase = make_codebase(m)

        graph = build_static_merged_graph(codebase, known_frameworks=frozenset({"pytest"}))

        # Edge to pytest.mark.skip is DIRECT (app imports pytest)
        for edge in graph.edges:
            if edge.callee_fqn == "pytest.mark.skip":
                assert edge.nature == EdgeNature.DIRECT
                break
