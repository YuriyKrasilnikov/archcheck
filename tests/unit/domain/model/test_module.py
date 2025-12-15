"""Tests for domain/model/module.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.class_ import Class
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.import_ import Import
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_import(module: str = "os") -> Import:
    """Create a valid Import."""
    return Import(module=module, name=None, alias=None, location=make_location())


def make_function(name: str = "func", is_method: bool = False) -> Function:
    """Create a valid Function."""
    return Function(
        name=name,
        qualified_name=f"module.{name}",
        parameters=(),
        return_annotation=None,
        decorators=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
        is_method=is_method,
    )


def make_class(name: str = "MyClass") -> Class:
    """Create a valid Class."""
    return Class(
        name=name,
        qualified_name=f"module.{name}",
        bases=(),
        decorators=(),
        methods=(),
        attributes=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
    )


def make_minimal_module(
    name: str = "mypackage.mymodule",
    path: Path = Path("src/mypackage/mymodule.py"),
    **kwargs: object,
) -> Module:
    """Create a minimal valid Module."""
    defaults: dict[str, object] = {
        "imports": (),
        "classes": (),
        "functions": (),
        "constants": (),
    }
    defaults.update(kwargs)
    return Module(name=name, path=path, **defaults)  # type: ignore[arg-type]


class TestModuleCreation:
    """Tests for valid Module creation."""

    def test_minimal_valid(self) -> None:
        mod = make_minimal_module()
        assert mod.name == "mypackage.mymodule"
        assert mod.path == Path("src/mypackage/mymodule.py")
        assert mod.imports == ()
        assert mod.classes == ()
        assert mod.functions == ()
        assert mod.constants == ()
        assert mod.docstring is None

    def test_with_imports(self) -> None:
        imports = (make_import("os"), make_import("sys"))
        mod = make_minimal_module(imports=imports)
        assert mod.imports == imports

    def test_with_classes(self) -> None:
        classes = (make_class("Foo"), make_class("Bar"))
        mod = make_minimal_module(classes=classes)
        assert mod.classes == classes

    def test_with_functions(self) -> None:
        funcs = (make_function("main"), make_function("helper"))
        mod = make_minimal_module(functions=funcs)
        assert mod.functions == funcs

    def test_with_constants(self) -> None:
        mod = make_minimal_module(constants=("MAX_SIZE", "DEFAULT_VALUE"))
        assert mod.constants == ("MAX_SIZE", "DEFAULT_VALUE")

    def test_with_docstring(self) -> None:
        mod = make_minimal_module(docstring="Module docstring.")
        assert mod.docstring == "Module docstring."

    def test_top_level_module(self) -> None:
        mod = make_minimal_module(name="main", path=Path("main.py"))
        assert mod.name == "main"

    def test_is_frozen(self) -> None:
        mod = make_minimal_module()
        with pytest.raises(AttributeError):
            mod.name = "other"  # type: ignore[misc]


class TestModuleFailFirst:
    """Tests for FAIL-FIRST validation in Module."""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="module name must not be empty"):
            make_minimal_module(name="")

    def test_method_in_functions_raises(self) -> None:
        method = make_function("do_something", is_method=True)
        with pytest.raises(ValueError, match="module-level function.*must have is_method=False"):
            make_minimal_module(functions=(method,))


class TestModulePackage:
    """Tests for Module.package property."""

    def test_package_from_qualified_name(self) -> None:
        mod = make_minimal_module(name="mypackage.subpackage.mymodule")
        assert mod.package == "mypackage.subpackage"

    def test_top_level_module_empty_package(self) -> None:
        mod = make_minimal_module(name="main")
        assert mod.package == ""

    def test_single_level_package(self) -> None:
        mod = make_minimal_module(name="mypackage.module")
        assert mod.package == "mypackage"
