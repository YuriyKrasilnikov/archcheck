"""Tests for domain/predicates/class_predicates.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.class_ import Class
from archcheck.domain.model.decorator import Decorator
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.location import Location
from archcheck.domain.predicates.class_predicates import (
    has_name_ending_with,
    has_name_matching,
    inherits_from,
    is_abstract,
    is_dataclass,
    is_decorated_with,
    is_exception,
    is_protocol,
)


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_class(
    name: str = "MyClass",
    bases: tuple[str, ...] = (),
    decorators: tuple[Decorator, ...] = (),
    is_abstract: bool = False,
    is_dataclass: bool = False,
    is_protocol: bool = False,
    is_exception: bool = False,
) -> Class:
    """Create a valid Class for tests."""
    return Class(
        name=name,
        qualified_name=f"module.{name}",
        bases=bases,
        decorators=decorators,
        methods=(),
        attributes=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
        is_abstract=is_abstract,
        is_dataclass=is_dataclass,
        is_protocol=is_protocol,
        is_exception=is_exception,
    )


class TestInheritsFrom:
    """Tests for inherits_from predicate."""

    def test_exact_match(self) -> None:
        pred = inherits_from("BaseClass")
        cls = make_class(bases=("BaseClass",))
        assert pred(cls) is True

    def test_no_match(self) -> None:
        pred = inherits_from("OtherClass")
        cls = make_class(bases=("BaseClass",))
        assert pred(cls) is False

    def test_wildcard_match(self) -> None:
        pred = inherits_from("*Repository")
        cls = make_class(bases=("UserRepository",))
        assert pred(cls) is True

    def test_multiple_bases(self) -> None:
        pred = inherits_from("Mixin")
        cls = make_class(bases=("BaseClass", "Mixin", "Protocol"))
        assert pred(cls) is True

    def test_no_bases(self) -> None:
        pred = inherits_from("BaseClass")
        cls = make_class(bases=())
        assert pred(cls) is False


class TestIsDecoratedWith:
    """Tests for is_decorated_with predicate."""

    def test_exact_match(self) -> None:
        pred = is_decorated_with("dataclass")
        cls = make_class(decorators=(Decorator(name="dataclass"),))
        assert pred(cls) is True

    def test_no_match(self) -> None:
        pred = is_decorated_with("property")
        cls = make_class(decorators=(Decorator(name="dataclass"),))
        assert pred(cls) is False

    def test_wildcard_match(self) -> None:
        pred = is_decorated_with("pytest.*")
        cls = make_class(decorators=(Decorator(name="pytest.fixture"),))
        assert pred(cls) is True

    def test_multiple_decorators(self) -> None:
        pred = is_decorated_with("staticmethod")
        cls = make_class(
            decorators=(
                Decorator(name="dataclass"),
                Decorator(name="staticmethod"),
            )
        )
        assert pred(cls) is True

    def test_no_decorators(self) -> None:
        pred = is_decorated_with("dataclass")
        cls = make_class(decorators=())
        assert pred(cls) is False


class TestIsAbstract:
    """Tests for is_abstract predicate."""

    def test_abstract_class(self) -> None:
        pred = is_abstract()
        cls = make_class(is_abstract=True)
        assert pred(cls) is True

    def test_non_abstract_class(self) -> None:
        pred = is_abstract()
        cls = make_class(is_abstract=False)
        assert pred(cls) is False


class TestIsDataclass:
    """Tests for is_dataclass predicate."""

    def test_dataclass(self) -> None:
        pred = is_dataclass()
        cls = make_class(is_dataclass=True)
        assert pred(cls) is True

    def test_non_dataclass(self) -> None:
        pred = is_dataclass()
        cls = make_class(is_dataclass=False)
        assert pred(cls) is False


class TestIsProtocol:
    """Tests for is_protocol predicate."""

    def test_protocol_class(self) -> None:
        pred = is_protocol()
        cls = make_class(is_protocol=True)
        assert pred(cls) is True

    def test_non_protocol_class(self) -> None:
        pred = is_protocol()
        cls = make_class(is_protocol=False)
        assert pred(cls) is False


class TestIsException:
    """Tests for is_exception predicate."""

    def test_exception_class(self) -> None:
        pred = is_exception()
        cls = make_class(name="CustomError", is_exception=True)
        assert pred(cls) is True

    def test_non_exception_class(self) -> None:
        pred = is_exception()
        cls = make_class(is_exception=False)
        assert pred(cls) is False


class TestHasNameEndingWith:
    """Tests for has_name_ending_with predicate."""

    def test_matching_suffix(self) -> None:
        pred = has_name_ending_with("Service")
        cls = make_class(name="UserService")
        assert pred(cls) is True

    def test_non_matching_suffix(self) -> None:
        pred = has_name_ending_with("Repository")
        cls = make_class(name="UserService")
        assert pred(cls) is False

    def test_exact_match(self) -> None:
        pred = has_name_ending_with("Service")
        cls = make_class(name="Service")
        assert pred(cls) is True

    def test_empty_suffix(self) -> None:
        pred = has_name_ending_with("")
        cls = make_class(name="AnyClass")
        assert pred(cls) is True


class TestHasNameMatching:
    """Tests for has_name_matching predicate."""

    def test_simple_regex(self) -> None:
        pred = has_name_matching(r".*Service")
        cls = make_class(name="UserService")
        assert pred(cls) is True

    def test_no_match(self) -> None:
        pred = has_name_matching(r"^Test.*")
        cls = make_class(name="UserService")
        assert pred(cls) is False

    def test_partial_match(self) -> None:
        pred = has_name_matching(r"User")
        cls = make_class(name="UserService")
        assert pred(cls) is True

    def test_complex_regex(self) -> None:
        pred = has_name_matching(r"^[A-Z][a-z]+Service$")
        cls = make_class(name="UserService")
        assert pred(cls) is True

    def test_invalid_regex_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid regex"):
            has_name_matching(r"[invalid")
