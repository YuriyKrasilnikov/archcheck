"""Tests for domain/model/call_graph.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.call_graph import CallGraph
from archcheck.domain.model.call_info import CallInfo
from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.class_ import Class
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_call_info(name: str, line: int = 1) -> CallInfo:
    """Create a CallInfo for tests."""
    return CallInfo(
        callee_name=name,
        resolved_fqn=None,  # Unresolved for simplicity
        line=line,
        call_type=CallType.FUNCTION,
    )


def make_body_calls(*names: str) -> tuple[CallInfo, ...]:
    """Create tuple of CallInfo from names."""
    return tuple(make_call_info(name, i + 1) for i, name in enumerate(names))


def make_function(
    name: str,
    module_name: str,
    body_calls: tuple[CallInfo, ...] = (),
    is_method: bool = False,
    class_name: str | None = None,
) -> Function:
    """Create a valid Function for tests."""
    if is_method and class_name:
        qualified_name = f"{module_name}.{class_name}.{name}"
    else:
        qualified_name = f"{module_name}.{name}"

    return Function(
        name=name,
        qualified_name=qualified_name,
        parameters=(),
        return_annotation=None,
        decorators=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
        is_method=is_method,
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


class TestCallGraphCreation:
    """Tests for valid CallGraph creation."""

    def test_empty_graph(self) -> None:
        g = CallGraph.empty()
        assert g.function_count == 0
        assert g.call_count == 0

    def test_is_frozen(self) -> None:
        g = CallGraph.empty()
        with pytest.raises(AttributeError):
            g.graph = None  # type: ignore[misc]


class TestCallGraphFromModules:
    """Tests for CallGraph.from_modules class method."""

    def test_empty_modules(self) -> None:
        g = CallGraph.from_modules({})
        assert g.function_count == 0

    def test_function_without_calls(self) -> None:
        func = make_function("main", "myapp")
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        # Function without calls may not be in graph (no edges)
        assert g.calls("myapp.main") == frozenset()

    def test_function_with_calls(self) -> None:
        func = make_function("main", "myapp", body_calls=make_body_calls("print", "helper"))
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.calls("myapp.main") == frozenset({"print", "helper"})

    def test_method_calls(self) -> None:
        method = make_function(
            "process",
            "myapp",
            is_method=True,
            class_name="Service",
            body_calls=make_body_calls("self.helper", "print"),
        )
        cls = make_class("Service", "myapp", methods=(method,))
        mod = make_module("myapp", classes=(cls,))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.calls("myapp.Service.process") == frozenset({"self.helper", "print"})

    def test_multiple_functions(self) -> None:
        func_a = make_function("a", "myapp", body_calls=make_body_calls("b"))
        func_b = make_function("b", "myapp", body_calls=make_body_calls("c"))
        mod = make_module("myapp", functions=(func_a, func_b))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.has_call("myapp.a", "b")
        assert g.has_call("myapp.b", "c")


class TestCallGraphCalls:
    """Tests for CallGraph.calls method."""

    def test_function_with_calls(self) -> None:
        func = make_function("main", "myapp", body_calls=make_body_calls("foo", "bar"))
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.calls("myapp.main") == frozenset({"foo", "bar"})

    def test_function_without_calls(self) -> None:
        func = make_function("empty", "myapp")
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.calls("myapp.empty") == frozenset()

    def test_nonexistent_function(self) -> None:
        g = CallGraph.empty()
        assert g.calls("unknown.func") == frozenset()


class TestCallGraphCalledBy:
    """Tests for CallGraph.called_by method."""

    def test_function_called_by_multiple(self) -> None:
        func_a = make_function("a", "myapp", body_calls=make_body_calls("shared"))
        func_b = make_function("b", "myapp", body_calls=make_body_calls("shared"))
        mod = make_module("myapp", functions=(func_a, func_b))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.called_by("shared") == frozenset({"myapp.a", "myapp.b"})

    def test_function_not_called(self) -> None:
        func = make_function("lonely", "myapp")
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.called_by("myapp.lonely") == frozenset()

    def test_nonexistent_function(self) -> None:
        g = CallGraph.empty()
        assert g.called_by("unknown") == frozenset()


class TestCallGraphHasCall:
    """Tests for CallGraph.has_call method."""

    def test_existing_call(self) -> None:
        func = make_function("main", "myapp", body_calls=make_body_calls("helper"))
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.has_call("myapp.main", "helper")

    def test_nonexistent_call(self) -> None:
        func = make_function("main", "myapp", body_calls=make_body_calls("helper"))
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert not g.has_call("myapp.main", "other")


class TestCallGraphHasFunction:
    """Tests for CallGraph.has_function method."""

    def test_caller_in_graph(self) -> None:
        func = make_function("main", "myapp", body_calls=make_body_calls("helper"))
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.has_function("myapp.main")

    def test_callee_in_graph(self) -> None:
        func = make_function("main", "myapp", body_calls=make_body_calls("helper"))
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.has_function("helper")

    def test_nonexistent_function(self) -> None:
        g = CallGraph.empty()
        assert not g.has_function("unknown")


class TestCallGraphCounts:
    """Tests for CallGraph count properties."""

    def test_function_count(self) -> None:
        func = make_function("main", "myapp", body_calls=make_body_calls("helper"))
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        # Both caller and callee are nodes
        assert g.function_count == 2

    def test_call_count(self) -> None:
        func = make_function("main", "myapp", body_calls=make_body_calls("a", "b", "c"))
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert g.call_count == 3

    def test_functions_property(self) -> None:
        func = make_function("main", "myapp", body_calls=make_body_calls("helper"))
        mod = make_module("myapp", functions=(func,))
        g = CallGraph.from_modules({"myapp": mod})
        assert "myapp.main" in g.functions
        assert "helper" in g.functions
