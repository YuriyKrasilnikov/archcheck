"""Tests for domain/predicates/function_predicates.py."""

from pathlib import Path

from archcheck.domain.model.call_info import CallInfo
from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.decorator import Decorator
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.location import Location
from archcheck.domain.model.parameter import Parameter
from archcheck.domain.model.purity import PurityInfo
from archcheck.domain.predicates.function_predicates import (
    calls_function,
    has_all_parameters_annotated,
    has_decorator,
    has_return_annotation,
    is_async,
    is_method,
    is_private,
    is_public,
    is_pure,
)


def make_call_info(name: str) -> CallInfo:
    """Create a CallInfo for tests."""
    return CallInfo(
        callee_name=name,
        resolved_fqn=None,
        line=1,
        call_type=CallType.FUNCTION,
    )


def make_body_calls(*names: str) -> tuple[CallInfo, ...]:
    """Create tuple of CallInfo from names."""
    return tuple(make_call_info(name) for name in names)


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_function(
    name: str = "func",
    visibility: Visibility = Visibility.PUBLIC,
    is_async: bool = False,
    is_method: bool = False,
    decorators: tuple[Decorator, ...] = (),
    purity_info: PurityInfo | None = None,
    body_calls: tuple[CallInfo, ...] = (),
    return_annotation: str | None = None,
    parameters: tuple[Parameter, ...] = (),
) -> Function:
    """Create a valid Function for tests."""
    return Function(
        name=name,
        qualified_name=f"module.{name}",
        parameters=parameters,
        return_annotation=return_annotation,
        decorators=decorators,
        location=make_location(),
        visibility=visibility,
        is_async=is_async,
        is_method=is_method,
        purity_info=purity_info,
        body_calls=body_calls,
    )


class TestIsPure:
    """Tests for is_pure predicate."""

    def test_pure_function(self) -> None:
        pred = is_pure()
        func = make_function(purity_info=PurityInfo(is_pure=True))
        assert pred(func) is True

    def test_impure_function(self) -> None:
        pred = is_pure()
        func = make_function(purity_info=PurityInfo(is_pure=False, has_io_calls=True))
        assert pred(func) is False

    def test_no_purity_info(self) -> None:
        pred = is_pure()
        func = make_function(purity_info=None)
        assert pred(func) is False


class TestIsPublic:
    """Tests for is_public predicate."""

    def test_public_function(self) -> None:
        pred = is_public()
        func = make_function(visibility=Visibility.PUBLIC)
        assert pred(func) is True

    def test_protected_function(self) -> None:
        pred = is_public()
        func = make_function(name="_helper", visibility=Visibility.PROTECTED)
        assert pred(func) is False

    def test_private_function(self) -> None:
        pred = is_public()
        func = make_function(name="__internal", visibility=Visibility.PRIVATE)
        assert pred(func) is False


class TestIsPrivate:
    """Tests for is_private predicate."""

    def test_private_function(self) -> None:
        pred = is_private()
        func = make_function(name="__internal", visibility=Visibility.PRIVATE)
        assert pred(func) is True

    def test_public_function(self) -> None:
        pred = is_private()
        func = make_function(visibility=Visibility.PUBLIC)
        assert pred(func) is False

    def test_protected_function(self) -> None:
        pred = is_private()
        func = make_function(name="_helper", visibility=Visibility.PROTECTED)
        assert pred(func) is False


class TestIsAsync:
    """Tests for is_async predicate."""

    def test_async_function(self) -> None:
        pred = is_async()
        func = make_function(is_async=True)
        assert pred(func) is True

    def test_sync_function(self) -> None:
        pred = is_async()
        func = make_function(is_async=False)
        assert pred(func) is False


class TestIsMethod:
    """Tests for is_method predicate."""

    def test_method(self) -> None:
        pred = is_method()
        func = make_function(is_method=True)
        assert pred(func) is True

    def test_function(self) -> None:
        pred = is_method()
        func = make_function(is_method=False)
        assert pred(func) is False


class TestHasDecorator:
    """Tests for has_decorator predicate."""

    def test_exact_match(self) -> None:
        pred = has_decorator("staticmethod")
        func = make_function(decorators=(Decorator(name="staticmethod"),), is_method=True)
        assert pred(func) is True

    def test_no_match(self) -> None:
        pred = has_decorator("classmethod")
        func = make_function(decorators=(Decorator(name="staticmethod"),), is_method=True)
        assert pred(func) is False

    def test_wildcard_match(self) -> None:
        pred = has_decorator("pytest.*")
        func = make_function(decorators=(Decorator(name="pytest.fixture"),))
        assert pred(func) is True

    def test_no_decorators(self) -> None:
        pred = has_decorator("any")
        func = make_function(decorators=())
        assert pred(func) is False


class TestCallsFunction:
    """Tests for calls_function predicate."""

    def test_exact_match(self) -> None:
        pred = calls_function("print")
        func = make_function(body_calls=make_body_calls("print", "len"))
        assert pred(func) is True

    def test_no_match(self) -> None:
        pred = calls_function("open")
        func = make_function(body_calls=make_body_calls("print", "len"))
        assert pred(func) is False

    def test_wildcard_match(self) -> None:
        pred = calls_function("os.*")
        func = make_function(body_calls=make_body_calls("os.path.join"))
        assert pred(func) is True

    def test_empty_calls(self) -> None:
        pred = calls_function("any")
        func = make_function(body_calls=())
        assert pred(func) is False


class TestHasReturnAnnotation:
    """Tests for has_return_annotation predicate."""

    def test_with_annotation(self) -> None:
        pred = has_return_annotation()
        func = make_function(return_annotation="int")
        assert pred(func) is True

    def test_without_annotation(self) -> None:
        pred = has_return_annotation()
        func = make_function(return_annotation=None)
        assert pred(func) is False


class TestHasAllParametersAnnotated:
    """Tests for has_all_parameters_annotated predicate."""

    def test_all_annotated(self) -> None:
        pred = has_all_parameters_annotated()
        params = (
            Parameter(name="x", annotation="int"),
            Parameter(name="y", annotation="str"),
        )
        func = make_function(parameters=params)
        assert pred(func) is True

    def test_some_not_annotated(self) -> None:
        pred = has_all_parameters_annotated()
        params = (
            Parameter(name="x", annotation="int"),
            Parameter(name="y"),  # no annotation
        )
        func = make_function(parameters=params)
        assert pred(func) is False

    def test_none_annotated(self) -> None:
        pred = has_all_parameters_annotated()
        params = (
            Parameter(name="x"),
            Parameter(name="y"),
        )
        func = make_function(parameters=params)
        assert pred(func) is False

    def test_empty_parameters(self) -> None:
        pred = has_all_parameters_annotated()
        func = make_function(parameters=())
        assert pred(func) is True  # vacuous truth
