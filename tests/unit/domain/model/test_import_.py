"""Tests for domain/model/import_.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.import_ import Import
from archcheck.domain.model.location import Location


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


class TestImportCreation:
    """Tests for valid Import creation."""

    def test_import_module(self) -> None:
        imp = Import(module="os", name=None, alias=None, location=make_location())
        assert imp.module == "os"
        assert imp.name is None
        assert imp.alias is None

    def test_from_import(self) -> None:
        imp = Import(module="os.path", name="join", alias=None, location=make_location())
        assert imp.module == "os.path"
        assert imp.name == "join"

    def test_import_with_alias(self) -> None:
        imp = Import(module="numpy", name=None, alias="np", location=make_location())
        assert imp.alias == "np"

    def test_from_import_with_alias(self) -> None:
        imp = Import(module="typing", name="Optional", alias="Opt", location=make_location())
        assert imp.name == "Optional"
        assert imp.alias == "Opt"

    def test_type_checking_import(self) -> None:
        imp = Import(
            module="mymodule",
            name="MyClass",
            alias=None,
            location=make_location(),
            is_type_checking=True,
        )
        assert imp.is_type_checking is True

    def test_conditional_import(self) -> None:
        imp = Import(
            module="optional_dep",
            name=None,
            alias=None,
            location=make_location(),
            is_conditional=True,
        )
        assert imp.is_conditional is True

    def test_lazy_import(self) -> None:
        imp = Import(
            module="heavy_module",
            name=None,
            alias=None,
            location=make_location(),
            is_lazy=True,
        )
        assert imp.is_lazy is True

    def test_default_flags(self) -> None:
        imp = Import(module="os", name=None, alias=None, location=make_location())
        assert imp.level == 0
        assert imp.is_type_checking is False
        assert imp.is_conditional is False
        assert imp.is_lazy is False

    def test_relative_import_level_1(self) -> None:
        """from . import foo → level=1, module resolved to absolute."""
        imp = Import(
            module="myapp.utils",  # resolved from relative
            name="helper",
            alias=None,
            location=make_location(),
            level=1,
        )
        assert imp.level == 1
        assert imp.module == "myapp.utils"

    def test_relative_import_level_2(self) -> None:
        """from .. import foo → level=2, module resolved to absolute."""
        imp = Import(
            module="myapp",  # resolved from relative
            name="core",
            alias=None,
            location=make_location(),
            level=2,
        )
        assert imp.level == 2
        assert imp.module == "myapp"

    def test_absolute_import_level_0(self) -> None:
        """import os → level=0."""
        imp = Import(module="os", name=None, alias=None, location=make_location(), level=0)
        assert imp.level == 0

    def test_is_frozen(self) -> None:
        imp = Import(module="os", name=None, alias=None, location=make_location())
        with pytest.raises(AttributeError):
            imp.module = "sys"  # type: ignore[misc]


class TestImportFailFirst:
    """Tests for FAIL-FIRST validation in Import."""

    def test_empty_module_raises(self) -> None:
        with pytest.raises(ValueError, match="import module must not be empty"):
            Import(module="", name=None, alias=None, location=make_location())

    def test_negative_level_raises(self) -> None:
        with pytest.raises(ValueError, match="level must be >= 0, got -1"):
            Import(module="os", name=None, alias=None, location=make_location(), level=-1)

    def test_empty_alias_raises(self) -> None:
        with pytest.raises(ValueError, match="alias must be non-empty string or None"):
            Import(module="os", name=None, alias="", location=make_location())


class TestImportImportedName:
    """Tests for Import.imported_name property."""

    def test_import_module_returns_last_part(self) -> None:
        imp = Import(module="os.path", name=None, alias=None, location=make_location())
        assert imp.imported_name == "path"

    def test_import_simple_module(self) -> None:
        imp = Import(module="os", name=None, alias=None, location=make_location())
        assert imp.imported_name == "os"

    def test_from_import_returns_name(self) -> None:
        imp = Import(module="os.path", name="join", alias=None, location=make_location())
        assert imp.imported_name == "join"

    def test_alias_takes_precedence(self) -> None:
        imp = Import(module="numpy", name=None, alias="np", location=make_location())
        assert imp.imported_name == "np"

    def test_alias_over_name(self) -> None:
        imp = Import(module="typing", name="Optional", alias="Opt", location=make_location())
        assert imp.imported_name == "Opt"
