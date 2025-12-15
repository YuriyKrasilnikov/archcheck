"""Tests for domain/model/decorator.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.decorator import Decorator
from archcheck.domain.model.location import Location


class TestDecoratorCreation:
    """Tests for valid Decorator creation."""

    def test_minimal_valid(self) -> None:
        dec = Decorator(name="property")
        assert dec.name == "property"
        assert dec.arguments == ()
        assert dec.location is None

    def test_with_arguments(self) -> None:
        dec = Decorator(name="dataclass", arguments=("frozen=True", "slots=True"))
        assert dec.arguments == ("frozen=True", "slots=True")

    def test_with_location(self) -> None:
        loc = Location(file=Path("test.py"), line=10, column=0)
        dec = Decorator(name="pytest.fixture", location=loc)
        assert dec.location == loc

    def test_dotted_name(self) -> None:
        dec = Decorator(name="functools.lru_cache")
        assert dec.name == "functools.lru_cache"

    def test_empty_arguments_tuple(self) -> None:
        dec = Decorator(name="staticmethod", arguments=())
        assert dec.arguments == ()

    def test_is_frozen(self) -> None:
        dec = Decorator(name="property")
        with pytest.raises(AttributeError):
            dec.name = "staticmethod"  # type: ignore[misc]


class TestDecoratorFailFirst:
    """Tests for FAIL-FIRST validation in Decorator."""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="decorator name must not be empty"):
            Decorator(name="")
