"""Tests for domain/model/symbol_table.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.import_ import Import
from archcheck.domain.model.location import Location
from archcheck.domain.model.symbol_table import SymbolTable


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_import(
    module: str,
    name: str | None = None,
    alias: str | None = None,
) -> Import:
    """Create a valid Import for tests."""
    return Import(
        module=module,
        name=name,
        alias=alias,
        location=make_location(),
    )


class TestSymbolTableCreation:
    """Tests for valid SymbolTable creation."""

    def test_empty_table(self) -> None:
        st = SymbolTable()
        assert st.size == 0
        assert st.all_names() == frozenset()

    def test_is_mutable(self) -> None:
        st = SymbolTable()
        st._direct["foo"] = "bar"  # Should not raise
        assert st._direct["foo"] == "bar"


class TestSymbolTableAddImport:
    """Tests for SymbolTable.add_import method."""

    def test_import_module(self) -> None:
        # import os
        st = SymbolTable()
        st.add_import(make_import("os"))
        assert st.resolve("os") == "os"

    def test_import_module_as_alias(self) -> None:
        # import numpy as np
        st = SymbolTable()
        st.add_import(make_import("numpy", alias="np"))
        assert st.resolve("np") == "numpy"
        assert st.resolve("numpy") is None  # Original name not available

    def test_from_import(self) -> None:
        # from os import path
        st = SymbolTable()
        st.add_import(make_import("os", name="path"))
        assert st.resolve("path") == "os.path"

    def test_from_import_with_alias(self) -> None:
        # from os import path as p
        st = SymbolTable()
        st.add_import(make_import("os", name="path", alias="p"))
        assert st.resolve("p") == "os.path"
        assert st.resolve("path") is None

    def test_star_import(self) -> None:
        # from module import *
        st = SymbolTable()
        st.add_import(make_import("mymodule", name="*"))
        assert st.has_star_imports()
        assert st.star_import_modules == ("mymodule",)

    def test_multiple_star_imports(self) -> None:
        st = SymbolTable()
        st.add_import(make_import("mod1", name="*"))
        st.add_import(make_import("mod2", name="*"))
        assert st.star_import_modules == ("mod1", "mod2")


class TestSymbolTableAddImportFailFirst:
    """Tests for FAIL-FIRST validation in add_import."""

    def test_empty_name_raises(self) -> None:
        st = SymbolTable()
        imp = Import(
            module="os",
            name="",  # Empty string, not None
            alias=None,
            location=make_location(),
        )
        with pytest.raises(ValueError, match="import name must be non-empty string or None"):
            st.add_import(imp)


class TestSymbolTableResolve:
    """Tests for SymbolTable.resolve method."""

    def test_direct_match(self) -> None:
        st = SymbolTable()
        st.add_import(make_import("os"))
        assert st.resolve("os") == "os"

    def test_attribute_chain(self) -> None:
        # import os → os.path.join resolves to os.path.join
        st = SymbolTable()
        st.add_import(make_import("os"))
        assert st.resolve("os.path.join") == "os.path.join"

    def test_from_import_attribute_chain(self) -> None:
        # from pathlib import Path → Path.cwd() resolves to pathlib.Path.cwd
        st = SymbolTable()
        st.add_import(make_import("pathlib", name="Path"))
        assert st.resolve("Path.cwd") == "pathlib.Path.cwd"

    def test_unresolved_returns_none(self) -> None:
        st = SymbolTable()
        assert st.resolve("unknown") is None

    def test_star_import_resolution_returns_none(self) -> None:
        # Star import: resolve returns None, does NOT guess
        # Use has_star_imports() to check if unresolved might be from star
        st = SymbolTable()
        st.add_import(make_import("mymodule", name="*"))
        assert st.resolve("anything") is None
        assert st.has_star_imports()  # Caller can check this

    def test_direct_takes_precedence_over_star(self) -> None:
        # Direct import resolves, star import doesn't affect it
        st = SymbolTable()
        st.add_import(make_import("starmod", name="*"))
        st.add_import(make_import("specific", name="foo"))
        assert st.resolve("foo") == "specific.foo"

    def test_star_import_with_dotted_unresolved_name(self) -> None:
        # Dotted name where first part not directly imported → None
        st = SymbolTable()
        st.add_import(make_import("starmod", name="*"))
        # "unknown.method" - "unknown" not in direct imports
        assert st.resolve("unknown.method") is None
        assert st.has_star_imports()  # Caller can check this


class TestSymbolTableResolveFailFirst:
    """Tests for FAIL-FIRST validation in resolve."""

    def test_empty_name_raises(self) -> None:
        st = SymbolTable()
        with pytest.raises(ValueError, match="name must not be empty"):
            st.resolve("")


class TestSymbolTableAllNames:
    """Tests for SymbolTable.all_names method."""

    def test_empty(self) -> None:
        st = SymbolTable()
        assert st.all_names() == frozenset()

    def test_with_imports(self) -> None:
        st = SymbolTable()
        st.add_import(make_import("os"))
        st.add_import(make_import("sys"))
        assert st.all_names() == frozenset({"os", "sys"})

    def test_excludes_star_imports(self) -> None:
        st = SymbolTable()
        st.add_import(make_import("os"))
        st.add_import(make_import("starmod", name="*"))
        assert st.all_names() == frozenset({"os"})


class TestSymbolTableHasStarImports:
    """Tests for SymbolTable.has_star_imports method."""

    def test_no_star_imports(self) -> None:
        st = SymbolTable()
        st.add_import(make_import("os"))
        assert not st.has_star_imports()

    def test_with_star_imports(self) -> None:
        st = SymbolTable()
        st.add_import(make_import("mod", name="*"))
        assert st.has_star_imports()


class TestSymbolTableSize:
    """Tests for SymbolTable.size property."""

    def test_empty(self) -> None:
        st = SymbolTable()
        assert st.size == 0

    def test_with_imports(self) -> None:
        st = SymbolTable()
        st.add_import(make_import("os"))
        st.add_import(make_import("sys"))
        assert st.size == 2

    def test_star_imports_not_counted(self) -> None:
        st = SymbolTable()
        st.add_import(make_import("os"))
        st.add_import(make_import("mod", name="*"))
        assert st.size == 1
