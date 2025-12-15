"""Tests for domain/model/import_graph.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.import_ import Import
from archcheck.domain.model.import_graph import ImportGraph
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_import(module: str) -> Import:
    """Create a valid Import for tests."""
    return Import(
        module=module,
        name=None,
        alias=None,
        location=make_location(),
    )


def make_module(name: str, imports: tuple[str, ...] = ()) -> Module:
    """Create a valid Module with imports."""
    return Module(
        name=name,
        path=Path(f"src/{name.replace('.', '/')}.py"),
        imports=tuple(make_import(imp) for imp in imports),
        classes=(),
        functions=(),
        constants=(),
    )


class TestImportGraphCreation:
    """Tests for valid ImportGraph creation."""

    def test_empty_graph(self) -> None:
        g = ImportGraph.empty()
        assert g.module_count == 0
        assert g.import_count == 0

    def test_is_frozen(self) -> None:
        g = ImportGraph.empty()
        with pytest.raises(AttributeError):
            g.graph = None  # type: ignore[misc]


class TestImportGraphFromModules:
    """Tests for ImportGraph.from_modules class method."""

    def test_empty_modules(self) -> None:
        g = ImportGraph.from_modules({})
        assert g.module_count == 0

    def test_single_module_no_imports(self) -> None:
        mod = make_module("myapp.core")
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert g.has_module("myapp.core")
        assert g.imports_of("myapp.core") == frozenset()

    def test_single_module_with_imports(self) -> None:
        mod = make_module("myapp.core", imports=("os", "sys"))
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert g.imports_of("myapp.core") == frozenset({"os", "sys"})

    def test_multiple_modules(self) -> None:
        mod_a = make_module("myapp.a", imports=("myapp.b",))
        mod_b = make_module("myapp.b", imports=("myapp.c",))
        mod_c = make_module("myapp.c")
        g = ImportGraph.from_modules(
            {
                "myapp.a": mod_a,
                "myapp.b": mod_b,
                "myapp.c": mod_c,
            }
        )
        assert g.has_import("myapp.a", "myapp.b")
        assert g.has_import("myapp.b", "myapp.c")
        assert not g.has_import("myapp.c", "myapp.a")

    def test_includes_all_modules_as_nodes(self) -> None:
        # Module with no imports should still be in graph
        mod = make_module("myapp.isolated")
        g = ImportGraph.from_modules({"myapp.isolated": mod})
        assert g.has_module("myapp.isolated")


class TestImportGraphImportsOf:
    """Tests for ImportGraph.imports_of method."""

    def test_module_with_imports(self) -> None:
        mod = make_module("myapp.core", imports=("os", "sys", "typing"))
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert g.imports_of("myapp.core") == frozenset({"os", "sys", "typing"})

    def test_module_without_imports(self) -> None:
        mod = make_module("myapp.empty")
        g = ImportGraph.from_modules({"myapp.empty": mod})
        assert g.imports_of("myapp.empty") == frozenset()

    def test_nonexistent_module(self) -> None:
        g = ImportGraph.empty()
        assert g.imports_of("unknown") == frozenset()


class TestImportGraphImportedBy:
    """Tests for ImportGraph.imported_by method."""

    def test_module_imported_by_multiple(self) -> None:
        mod_a = make_module("myapp.a", imports=("myapp.shared",))
        mod_b = make_module("myapp.b", imports=("myapp.shared",))
        mod_shared = make_module("myapp.shared")
        g = ImportGraph.from_modules(
            {
                "myapp.a": mod_a,
                "myapp.b": mod_b,
                "myapp.shared": mod_shared,
            }
        )
        assert g.imported_by("myapp.shared") == frozenset({"myapp.a", "myapp.b"})

    def test_module_not_imported(self) -> None:
        mod = make_module("myapp.isolated")
        g = ImportGraph.from_modules({"myapp.isolated": mod})
        assert g.imported_by("myapp.isolated") == frozenset()


class TestImportGraphImportsFromPackage:
    """Tests for ImportGraph.imports_from_package method."""

    def test_filter_by_package(self) -> None:
        mod = make_module(
            "myapp.core",
            imports=("myapp.utils", "myapp.models.user", "os", "sys"),
        )
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert g.imports_from_package("myapp.core", "myapp") == frozenset(
            {
                "myapp.utils",
                "myapp.models.user",
            }
        )

    def test_exact_package_match(self) -> None:
        mod = make_module("myapp.core", imports=("myapp", "myapp.utils"))
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert g.imports_from_package("myapp.core", "myapp") == frozenset(
            {
                "myapp",
                "myapp.utils",
            }
        )

    def test_no_matching_imports(self) -> None:
        mod = make_module("myapp.core", imports=("os", "sys"))
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert g.imports_from_package("myapp.core", "myapp") == frozenset()


class TestImportGraphImportsFromPackageFailFirst:
    """Tests for FAIL-FIRST validation in imports_from_package."""

    def test_empty_package_raises(self) -> None:
        g = ImportGraph.empty()
        with pytest.raises(ValueError, match="package must not be empty"):
            g.imports_from_package("myapp.core", "")


class TestImportGraphHasImport:
    """Tests for ImportGraph.has_import method."""

    def test_existing_import(self) -> None:
        mod = make_module("myapp.core", imports=("os",))
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert g.has_import("myapp.core", "os")

    def test_nonexistent_import(self) -> None:
        mod = make_module("myapp.core", imports=("os",))
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert not g.has_import("myapp.core", "sys")


class TestImportGraphHasModule:
    """Tests for ImportGraph.has_module method."""

    def test_existing_module(self) -> None:
        mod = make_module("myapp.core")
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert g.has_module("myapp.core")

    def test_nonexistent_module(self) -> None:
        g = ImportGraph.empty()
        assert not g.has_module("unknown")


class TestImportGraphCounts:
    """Tests for ImportGraph count properties."""

    def test_module_count(self) -> None:
        mod_a = make_module("myapp.a")
        mod_b = make_module("myapp.b")
        g = ImportGraph.from_modules({"myapp.a": mod_a, "myapp.b": mod_b})
        assert g.module_count == 2

    def test_import_count(self) -> None:
        mod = make_module("myapp.core", imports=("os", "sys", "typing"))
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert g.import_count == 3

    def test_modules_property(self) -> None:
        mod = make_module("myapp.core")
        g = ImportGraph.from_modules({"myapp.core": mod})
        assert "myapp.core" in g.modules
