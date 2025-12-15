"""Tests for domain/model/function.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.decorator import Decorator
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.location import Location
from archcheck.domain.model.parameter import Parameter
from archcheck.domain.model.purity import PurityInfo


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_minimal_function(
    name: str = "func",
    qualified_name: str = "module.func",
    **kwargs: object,
) -> Function:
    """Create a minimal valid Function."""
    defaults: dict[str, object] = {
        "parameters": (),
        "return_annotation": None,
        "decorators": (),
        "location": make_location(),
        "visibility": Visibility.PUBLIC,
    }
    defaults.update(kwargs)
    return Function(name=name, qualified_name=qualified_name, **defaults)  # type: ignore[arg-type]


class TestFunctionCreation:
    """Tests for valid Function creation."""

    def test_minimal_valid(self) -> None:
        func = make_minimal_function()
        assert func.name == "func"
        assert func.qualified_name == "module.func"
        assert func.parameters == ()
        assert func.return_annotation is None
        assert func.decorators == ()
        assert func.visibility == Visibility.PUBLIC
        assert func.is_async is False
        assert func.is_generator is False
        assert func.is_method is False
        assert func.is_classmethod is False
        assert func.is_staticmethod is False
        assert func.is_property is False
        assert func.is_abstract is False
        assert func.purity_info is None
        assert func.body_calls == ()  # tuple[CallInfo, ...] is empty by default
        assert func.body_attributes == frozenset()
        assert func.body_globals_read == frozenset()
        assert func.body_globals_write == frozenset()

    def test_with_parameters(self) -> None:
        params = (Parameter(name="x", annotation="int"), Parameter(name="y", annotation="str"))
        func = make_minimal_function(parameters=params)
        assert func.parameters == params

    def test_with_return_annotation(self) -> None:
        func = make_minimal_function(return_annotation="int")
        assert func.return_annotation == "int"

    def test_with_decorators(self) -> None:
        decs = (Decorator(name="staticmethod"),)
        func = make_minimal_function(decorators=decs, is_method=True, is_staticmethod=True)
        assert func.decorators == decs

    def test_async_function(self) -> None:
        func = make_minimal_function(is_async=True)
        assert func.is_async is True

    def test_generator_function(self) -> None:
        func = make_minimal_function(is_generator=True)
        assert func.is_generator is True

    def test_method(self) -> None:
        func = make_minimal_function(
            name="do_something",
            qualified_name="module.MyClass.do_something",
            is_method=True,
        )
        assert func.is_method is True

    def test_classmethod(self) -> None:
        func = make_minimal_function(
            name="from_dict",
            qualified_name="module.MyClass.from_dict",
            is_method=True,
            is_classmethod=True,
        )
        assert func.is_classmethod is True

    def test_staticmethod(self) -> None:
        func = make_minimal_function(
            name="utility",
            qualified_name="module.MyClass.utility",
            is_method=True,
            is_staticmethod=True,
        )
        assert func.is_staticmethod is True

    def test_property(self) -> None:
        func = make_minimal_function(
            name="value",
            qualified_name="module.MyClass.value",
            is_method=True,
            is_property=True,
        )
        assert func.is_property is True

    def test_abstract_method(self) -> None:
        func = make_minimal_function(
            name="process",
            qualified_name="module.AbstractClass.process",
            is_method=True,
            is_abstract=True,
        )
        assert func.is_abstract is True

    def test_with_purity_info(self) -> None:
        purity = PurityInfo(is_pure=True)
        func = make_minimal_function(purity_info=purity)
        assert func.purity_info == purity

    def test_with_body_analysis(self) -> None:
        func = make_minimal_function(
            body_calls=frozenset(["print", "len"]),
            body_attributes=frozenset(["self.x", "obj.y"]),
            body_globals_read=frozenset(["CONFIG"]),
            body_globals_write=frozenset(["COUNTER"]),
        )
        assert func.body_calls == frozenset(["print", "len"])
        assert func.body_attributes == frozenset(["self.x", "obj.y"])
        assert func.body_globals_read == frozenset(["CONFIG"])
        assert func.body_globals_write == frozenset(["COUNTER"])

    def test_protected_visibility(self) -> None:
        func = make_minimal_function(
            name="_helper",
            qualified_name="module._helper",
            visibility=Visibility.PROTECTED,
        )
        assert func.visibility == Visibility.PROTECTED

    def test_private_visibility(self) -> None:
        func = make_minimal_function(
            name="__internal",
            qualified_name="module.__internal",
            visibility=Visibility.PRIVATE,
        )
        assert func.visibility == Visibility.PRIVATE

    def test_is_frozen(self) -> None:
        func = make_minimal_function()
        with pytest.raises(AttributeError):
            func.name = "other"  # type: ignore[misc]


class TestFunctionFailFirst:
    """Tests for FAIL-FIRST validation in Function."""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="function name must not be empty"):
            make_minimal_function(name="", qualified_name="module.")

    def test_empty_qualified_name_raises(self) -> None:
        with pytest.raises(ValueError, match="qualified_name must not be empty"):
            make_minimal_function(name="func", qualified_name="")

    def test_name_not_in_qualified_name_raises(self) -> None:
        with pytest.raises(ValueError, match="qualified_name.*must contain name"):
            make_minimal_function(name="func", qualified_name="module.other")

    def test_classmethod_and_staticmethod_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be both classmethod and staticmethod"):
            make_minimal_function(
                is_method=True,
                is_classmethod=True,
                is_staticmethod=True,
            )

    def test_property_and_staticmethod_raises(self) -> None:
        with pytest.raises(ValueError, match="property cannot be staticmethod"):
            make_minimal_function(
                is_method=True,
                is_property=True,
                is_staticmethod=True,
            )

    def test_classmethod_without_is_method_raises(self) -> None:
        with pytest.raises(ValueError, match="classmethod must have is_method=True"):
            make_minimal_function(is_classmethod=True, is_method=False)

    def test_staticmethod_without_is_method_raises(self) -> None:
        with pytest.raises(ValueError, match="staticmethod must have is_method=True"):
            make_minimal_function(is_staticmethod=True, is_method=False)

    def test_property_without_is_method_raises(self) -> None:
        with pytest.raises(ValueError, match="property must have is_method=True"):
            make_minimal_function(is_property=True, is_method=False)
