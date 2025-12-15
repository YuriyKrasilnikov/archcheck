"""Tests for domain/model/parameter.py."""

import pytest

from archcheck.domain.model.parameter import Parameter


class TestParameterCreation:
    """Tests for valid Parameter creation."""

    def test_minimal_valid(self) -> None:
        param = Parameter(name="x")
        assert param.name == "x"
        assert param.annotation is None
        assert param.default is None
        assert param.is_positional_only is False
        assert param.is_keyword_only is False
        assert param.is_variadic is False
        assert param.is_variadic_keyword is False

    def test_with_annotation(self) -> None:
        param = Parameter(name="x", annotation="int")
        assert param.annotation == "int"

    def test_with_default(self) -> None:
        param = Parameter(name="x", default="42")
        assert param.default == "42"

    def test_with_complex_annotation(self) -> None:
        param = Parameter(name="x", annotation="list[dict[str, int]]")
        assert param.annotation == "list[dict[str, int]]"

    def test_positional_only(self) -> None:
        param = Parameter(name="x", is_positional_only=True)
        assert param.is_positional_only is True

    def test_keyword_only(self) -> None:
        param = Parameter(name="x", is_keyword_only=True)
        assert param.is_keyword_only is True

    def test_variadic_args(self) -> None:
        param = Parameter(name="args", is_variadic=True)
        assert param.is_variadic is True

    def test_variadic_kwargs(self) -> None:
        param = Parameter(name="kwargs", is_variadic_keyword=True)
        assert param.is_variadic_keyword is True

    def test_is_frozen(self) -> None:
        param = Parameter(name="x")
        with pytest.raises(AttributeError):
            param.name = "y"  # type: ignore[misc]


class TestParameterFailFirst:
    """Tests for FAIL-FIRST validation in Parameter."""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="parameter name must not be empty"):
            Parameter(name="")

    def test_both_variadic_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be both.*args.*kwargs"):
            Parameter(name="x", is_variadic=True, is_variadic_keyword=True)

    def test_positional_and_keyword_only_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be both positional-only and keyword-only"):
            Parameter(name="x", is_positional_only=True, is_keyword_only=True)

    def test_variadic_positional_only_raises(self) -> None:
        with pytest.raises(ValueError, match="args cannot be positional-only"):
            Parameter(name="args", is_variadic=True, is_positional_only=True)

    def test_variadic_keyword_only_raises(self) -> None:
        with pytest.raises(ValueError, match="args cannot be.*keyword-only"):
            Parameter(name="args", is_variadic=True, is_keyword_only=True)

    def test_variadic_keyword_positional_only_raises(self) -> None:
        with pytest.raises(ValueError, match="kwargs cannot be positional-only"):
            Parameter(name="kwargs", is_variadic_keyword=True, is_positional_only=True)

    def test_variadic_keyword_keyword_only_raises(self) -> None:
        with pytest.raises(ValueError, match="kwargs cannot be.*keyword-only"):
            Parameter(name="kwargs", is_variadic_keyword=True, is_keyword_only=True)
