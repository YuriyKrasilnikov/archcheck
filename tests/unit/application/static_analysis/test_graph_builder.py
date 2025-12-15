"""Tests for StaticCallGraphBuilder."""

from pathlib import Path

import pytest

from archcheck.application.static_analysis.graph_builder import StaticCallGraphBuilder
from archcheck.domain.model.call_info import CallInfo
from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.class_ import Class
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.decorator import Decorator
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_call_info(
    name: str,
    resolved_fqn: str | None = None,
    line: int = 1,
    call_type: CallType = CallType.FUNCTION,
) -> CallInfo:
    """Create a CallInfo for tests."""
    return CallInfo(
        callee_name=name,
        resolved_fqn=resolved_fqn,
        line=line,
        call_type=call_type,
    )


def make_function(
    name: str,
    module_name: str,
    class_name: str | None = None,
    body_calls: tuple[CallInfo, ...] = (),
    decorators: tuple[Decorator, ...] = (),
) -> Function:
    """Create a valid Function for tests."""
    if class_name:
        qualified_name = f"{module_name}.{class_name}.{name}"
    else:
        qualified_name = f"{module_name}.{name}"

    return Function(
        name=name,
        qualified_name=qualified_name,
        parameters=(),
        return_annotation=None,
        decorators=decorators,
        location=make_location(),
        visibility=Visibility.PUBLIC,
        is_method=class_name is not None,
        body_calls=body_calls,
    )


def make_class(
    name: str,
    module_name: str,
    methods: tuple[Function, ...] = (),
) -> Class:
    """Create a valid Class for tests."""
    return Class(
        name=name,
        qualified_name=f"{module_name}.{name}",
        bases=(),
        decorators=(),
        methods=methods,
        attributes=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
    )


def make_module(
    name: str,
    functions: tuple[Function, ...] = (),
    classes: tuple[Class, ...] = (),
) -> Module:
    """Create a valid Module for tests."""
    return Module(
        name=name,
        path=Path(f"src/{name.replace('.', '/')}.py"),
        imports=(),
        classes=classes,
        functions=functions,
        constants=(),
    )


def make_codebase(*modules: Module) -> Codebase:
    """Create a Codebase from modules."""
    codebase = Codebase(root_path=Path("src"), root_package="myapp")
    for module in modules:
        codebase.add_module(module)
    return codebase


class TestStaticCallGraphBuilderFailFirst:
    """Test FAIL-FIRST validation."""

    def test_none_codebase_raises(self) -> None:
        """None codebase raises TypeError."""
        builder = StaticCallGraphBuilder()
        with pytest.raises(TypeError, match="codebase must not be None"):
            builder.build(None)  # type: ignore[arg-type]


class TestStaticCallGraphBuilderEmpty:
    """Test empty codebase handling."""

    def test_empty_codebase(self) -> None:
        """Empty codebase produces empty graph."""
        codebase = make_codebase()
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        assert graph.function_count == 0
        assert graph.edge_count == 0
        assert graph.decorator_count == 0


class TestStaticCallGraphBuilderFunctions:
    """Test function collection."""

    def test_module_function_collected(self) -> None:
        """Module-level function is added to functions set."""
        func = make_function("process", "myapp.service")
        module = make_module("myapp.service", functions=(func,))
        codebase = make_codebase(module)
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        assert "myapp.service.process" in graph.functions

    def test_method_collected(self) -> None:
        """Class method is added to functions set."""
        method = make_function("handle", "myapp.handlers", class_name="Handler")
        cls = make_class("Handler", "myapp.handlers", methods=(method,))
        module = make_module("myapp.handlers", classes=(cls,))
        codebase = make_codebase(module)
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        assert "myapp.handlers.Handler.handle" in graph.functions


class TestStaticCallGraphBuilderDecorators:
    """Test decorator collection."""

    def test_decorator_collected(self) -> None:
        """Decorator is added to decorators set."""
        decorator = Decorator(name="property")
        func = make_function(
            "get_value",
            "myapp.model",
            decorators=(decorator,),
        )
        module = make_module("myapp.model", functions=(func,))
        codebase = make_codebase(module)
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        assert "property" in graph.decorators

    def test_multiple_decorators_collected(self) -> None:
        """Multiple decorators are all collected."""
        decorators = (
            Decorator(name="staticmethod"),
            Decorator(name="custom_decorator", arguments=("arg",)),
        )
        func = make_function("utility", "myapp.utils", decorators=decorators)
        module = make_module("myapp.utils", functions=(func,))
        codebase = make_codebase(module)
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        assert "staticmethod" in graph.decorators
        assert "custom_decorator" in graph.decorators


class TestStaticCallGraphBuilderEdges:
    """Test edge collection."""

    def test_resolved_call_creates_edge(self) -> None:
        """Resolved call creates an edge."""
        call = make_call_info(
            name="helper",
            resolved_fqn="myapp.utils.helper",
            line=10,
            call_type=CallType.FUNCTION,
        )
        func = make_function("main", "myapp.entry", body_calls=(call,))
        module = make_module("myapp.entry", functions=(func,))
        codebase = make_codebase(module)
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        assert graph.edge_count == 1
        edges = graph.get_edges_from("myapp.entry.main")
        assert len(edges) == 1
        edge = next(iter(edges))
        assert edge.caller_fqn == "myapp.entry.main"
        assert edge.callee_fqn == "myapp.utils.helper"
        assert edge.line == 10
        assert edge.call_type == CallType.FUNCTION

    def test_unresolved_call_no_edge(self) -> None:
        """Unresolved call does not create an edge."""
        call = make_call_info(
            name="external_lib_func",
            resolved_fqn=None,  # Not resolved
            line=5,
        )
        func = make_function("process", "myapp.handler", body_calls=(call,))
        module = make_module("myapp.handler", functions=(func,))
        codebase = make_codebase(module)
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        # Function is in graph but no edges
        assert "myapp.handler.process" in graph.functions
        assert graph.edge_count == 0

    def test_multiple_calls_create_multiple_edges(self) -> None:
        """Multiple resolved calls create multiple edges."""
        calls = (
            make_call_info("helper1", "myapp.utils.helper1", 10),
            make_call_info("helper2", "myapp.utils.helper2", 15),
            make_call_info("external", None, 20),  # Unresolved
        )
        func = make_function("main", "myapp.entry", body_calls=calls)
        module = make_module("myapp.entry", functions=(func,))
        codebase = make_codebase(module)
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        # Only 2 edges (unresolved call excluded)
        assert graph.edge_count == 2

    def test_method_call_creates_edge(self) -> None:
        """Method call creates an edge with METHOD call type."""
        call = make_call_info(
            name="self.validate",
            resolved_fqn="myapp.service.Service.validate",
            line=25,
            call_type=CallType.METHOD,
        )
        method = make_function(
            "process",
            "myapp.service",
            class_name="Service",
            body_calls=(call,),
        )
        cls = make_class("Service", "myapp.service", methods=(method,))
        module = make_module("myapp.service", classes=(cls,))
        codebase = make_codebase(module)
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        edges = graph.get_edges_from("myapp.service.Service.process")
        assert len(edges) == 1
        edge = next(iter(edges))
        assert edge.call_type == CallType.METHOD


class TestStaticCallGraphBuilderIntegration:
    """Integration tests with multiple modules."""

    def test_cross_module_calls(self) -> None:
        """Calls across modules create correct edges."""
        # Module A calls function in Module B
        call = make_call_info(
            name="utility",
            resolved_fqn="myapp.utils.utility",
            line=10,
        )
        func_a = make_function("main", "myapp.entry", body_calls=(call,))
        module_a = make_module("myapp.entry", functions=(func_a,))

        func_b = make_function("utility", "myapp.utils")
        module_b = make_module("myapp.utils", functions=(func_b,))

        codebase = make_codebase(module_a, module_b)
        builder = StaticCallGraphBuilder()

        graph = builder.build(codebase)

        # Both functions in graph
        assert "myapp.entry.main" in graph.functions
        assert "myapp.utils.utility" in graph.functions

        # Edge from A to B
        edges = graph.get_edges_from("myapp.entry.main")
        assert len(edges) == 1
        edge = next(iter(edges))
        assert edge.callee_fqn == "myapp.utils.utility"
