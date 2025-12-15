"""Tests for domain/model/class_.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.class_ import Class
from archcheck.domain.model.decorator import Decorator
from archcheck.domain.model.di import DIInfo
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.location import Location


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_method(
    name: str = "method",
    class_name: str = "MyClass",
    module: str = "module",
) -> Function:
    """Create a valid method Function."""
    return Function(
        name=name,
        qualified_name=f"{module}.{class_name}.{name}",
        parameters=(),
        return_annotation=None,
        decorators=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
        is_method=True,
    )


def make_minimal_class(
    name: str = "MyClass",
    qualified_name: str = "module.MyClass",
    **kwargs: object,
) -> Class:
    """Create a minimal valid Class."""
    defaults: dict[str, object] = {
        "bases": (),
        "decorators": (),
        "methods": (),
        "attributes": (),
        "location": make_location(),
        "visibility": Visibility.PUBLIC,
    }
    defaults.update(kwargs)
    return Class(name=name, qualified_name=qualified_name, **defaults)  # type: ignore[arg-type]


class TestClassCreation:
    """Tests for valid Class creation."""

    def test_minimal_valid(self) -> None:
        cls = make_minimal_class()
        assert cls.name == "MyClass"
        assert cls.qualified_name == "module.MyClass"
        assert cls.bases == ()
        assert cls.decorators == ()
        assert cls.methods == ()
        assert cls.attributes == ()
        assert cls.visibility == Visibility.PUBLIC
        assert cls.is_abstract is False
        assert cls.is_dataclass is False
        assert cls.is_protocol is False
        assert cls.is_exception is False
        assert cls.docstring is None
        assert cls.di_info is None

    def test_with_bases(self) -> None:
        cls = make_minimal_class(bases=("BaseClass", "Mixin"))
        assert cls.bases == ("BaseClass", "Mixin")

    def test_with_decorators(self) -> None:
        decs = (Decorator(name="dataclass", arguments=("frozen=True",)),)
        cls = make_minimal_class(decorators=decs, is_dataclass=True)
        assert cls.decorators == decs

    def test_with_methods(self) -> None:
        methods = (make_method("__init__"), make_method("process"))
        cls = make_minimal_class(methods=methods)
        assert cls.methods == methods

    def test_with_attributes(self) -> None:
        cls = make_minimal_class(attributes=("x", "y", "name"))
        assert cls.attributes == ("x", "y", "name")

    def test_abstract_class(self) -> None:
        cls = make_minimal_class(is_abstract=True, bases=("ABC",))
        assert cls.is_abstract is True

    def test_dataclass(self) -> None:
        decs = (Decorator(name="dataclass"),)
        cls = make_minimal_class(is_dataclass=True, decorators=decs)
        assert cls.is_dataclass is True

    def test_protocol_class(self) -> None:
        cls = make_minimal_class(is_protocol=True, bases=("Protocol",))
        assert cls.is_protocol is True

    def test_exception_class(self) -> None:
        cls = make_minimal_class(
            name="CustomError",
            qualified_name="module.CustomError",
            is_exception=True,
            bases=("Exception",),
        )
        assert cls.is_exception is True

    def test_with_docstring(self) -> None:
        cls = make_minimal_class(docstring="This is my class.")
        assert cls.docstring == "This is my class."

    def test_with_di_info(self) -> None:
        di = DIInfo(
            has_constructor_injection=True,
            injected_dependencies=("Repository",),
        )
        cls = make_minimal_class(di_info=di)
        assert cls.di_info == di

    def test_protected_visibility(self) -> None:
        cls = make_minimal_class(
            name="_InternalClass",
            qualified_name="module._InternalClass",
            visibility=Visibility.PROTECTED,
        )
        assert cls.visibility == Visibility.PROTECTED

    def test_private_visibility(self) -> None:
        cls = make_minimal_class(
            name="__PrivateClass",
            qualified_name="module.__PrivateClass",
            visibility=Visibility.PRIVATE,
        )
        assert cls.visibility == Visibility.PRIVATE

    def test_is_frozen(self) -> None:
        cls = make_minimal_class()
        with pytest.raises(AttributeError):
            cls.name = "Other"  # type: ignore[misc]


class TestClassFailFirst:
    """Tests for FAIL-FIRST validation in Class."""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="class name must not be empty"):
            make_minimal_class(name="", qualified_name="module.")

    def test_empty_qualified_name_raises(self) -> None:
        with pytest.raises(ValueError, match="qualified_name must not be empty"):
            make_minimal_class(name="MyClass", qualified_name="")

    def test_name_not_in_qualified_name_raises(self) -> None:
        with pytest.raises(ValueError, match="qualified_name.*must contain name"):
            make_minimal_class(name="MyClass", qualified_name="module.OtherClass")

    def test_method_without_is_method_flag_raises(self) -> None:
        # Create a function that is NOT a method
        not_method = Function(
            name="func",
            qualified_name="module.MyClass.func",
            parameters=(),
            return_annotation=None,
            decorators=(),
            location=make_location(),
            visibility=Visibility.PUBLIC,
            is_method=False,  # This should cause validation error
        )
        with pytest.raises(ValueError, match="method.*must have is_method=True"):
            make_minimal_class(methods=(not_method,))
