"""Tests for domain/model/codebase.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.class_ import Class
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_function(name: str = "func", module_name: str = "mymodule") -> Function:
    """Create a valid module-level Function."""
    return Function(
        name=name,
        qualified_name=f"{module_name}.{name}",
        parameters=(),
        return_annotation=None,
        decorators=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
        is_method=False,
    )


def make_method(
    name: str = "method", class_name: str = "MyClass", module_name: str = "mymodule"
) -> Function:
    """Create a valid method Function."""
    return Function(
        name=name,
        qualified_name=f"{module_name}.{class_name}.{name}",
        parameters=(),
        return_annotation=None,
        decorators=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
        is_method=True,
    )


def make_class(
    name: str = "MyClass", module_name: str = "mymodule", methods: tuple[Function, ...] = ()
) -> Class:
    """Create a valid Class."""
    return Class(
        name=name,
        qualified_name=f"{module_name}.{name}",
        bases=(),
        decorators=(),
        methods=methods,
        attributes=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
    )


def make_module(
    name: str = "mymodule",
    functions: tuple[Function, ...] = (),
    classes: tuple[Class, ...] = (),
) -> Module:
    """Create a valid Module."""
    return Module(
        name=name,
        path=Path(f"src/{name.replace('.', '/')}.py"),
        imports=(),
        classes=classes,
        functions=functions,
        constants=(),
    )


class TestCodebaseCreation:
    """Tests for valid Codebase creation."""

    def test_minimal_valid(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        assert cb.root_path == Path("src")
        assert cb.root_package == "myapp"
        assert cb.modules == {}

    def test_is_mutable(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.root_package = "other"  # Should not raise - Codebase is mutable
        assert cb.root_package == "other"


class TestCodebaseFailFirst:
    """Tests for FAIL-FIRST validation in Codebase."""

    def test_empty_root_package_raises(self) -> None:
        with pytest.raises(ValueError, match="root_package must not be empty"):
            Codebase(root_path=Path("src"), root_package="")


class TestCodebaseGetModule:
    """Tests for Codebase.get_module method."""

    def test_get_existing_module(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        mod = make_module(name="myapp.core")
        cb.modules["myapp.core"] = mod

        assert cb.get_module("myapp.core") == mod

    def test_get_nonexistent_module_returns_none(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")

        assert cb.get_module("nonexistent") is None


class TestCodebaseGetClass:
    """Tests for Codebase.get_class method."""

    def test_get_existing_class(self) -> None:
        cls = make_class(name="Service", module_name="myapp.services")
        mod = make_module(name="myapp.services", classes=(cls,))
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.modules["myapp.services"] = mod

        assert cb.get_class("myapp.services.Service") == cls

    def test_get_nonexistent_class_returns_none(self) -> None:
        mod = make_module(name="myapp.services")
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.modules["myapp.services"] = mod

        assert cb.get_class("myapp.services.Missing") is None

    def test_get_nonexistent_class_with_other_classes(self) -> None:
        # Module has classes but the requested one is not among them
        cls = make_class(name="Foo", module_name="myapp.services")
        mod = make_module(name="myapp.services", classes=(cls,))
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.modules["myapp.services"] = mod

        assert cb.get_class("myapp.services.Bar") is None

    def test_get_class_nonexistent_module_returns_none(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")

        assert cb.get_class("nonexistent.Class") is None

    def test_get_class_invalid_qualified_name_returns_none(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")

        assert cb.get_class("nomodule") is None
        assert cb.get_class("") is None


class TestCodebaseIterModules:
    """Tests for Codebase.iter_modules method."""

    def test_empty_codebase(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")

        assert list(cb.iter_modules()) == []

    def test_with_modules(self) -> None:
        mod1 = make_module(name="myapp.a")
        mod2 = make_module(name="myapp.b")
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.modules["myapp.a"] = mod1
        cb.modules["myapp.b"] = mod2

        result = cb.iter_modules()
        assert set(result) == {mod1, mod2}


class TestCodebaseIterClasses:
    """Tests for Codebase.iter_classes method."""

    def test_empty_codebase(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")

        assert list(cb.iter_classes()) == []

    def test_classes_from_multiple_modules(self) -> None:
        cls1 = make_class(name="Foo", module_name="myapp.a")
        cls2 = make_class(name="Bar", module_name="myapp.b")
        mod1 = make_module(name="myapp.a", classes=(cls1,))
        mod2 = make_module(name="myapp.b", classes=(cls2,))

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.modules["myapp.a"] = mod1
        cb.modules["myapp.b"] = mod2

        result = list(cb.iter_classes())
        assert set(result) == {cls1, cls2}


class TestCodebaseIterFunctions:
    """Tests for Codebase.iter_functions method."""

    def test_empty_codebase(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")

        assert list(cb.iter_functions()) == []

    def test_module_level_functions(self) -> None:
        func1 = make_function(name="main", module_name="myapp.a")
        func2 = make_function(name="helper", module_name="myapp.b")
        mod1 = make_module(name="myapp.a", functions=(func1,))
        mod2 = make_module(name="myapp.b", functions=(func2,))

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.modules["myapp.a"] = mod1
        cb.modules["myapp.b"] = mod2

        result = list(cb.iter_functions())
        assert set(result) == {func1, func2}

    def test_includes_methods(self) -> None:
        method = make_method(name="process", class_name="Service", module_name="myapp.services")
        cls = make_class(name="Service", module_name="myapp.services", methods=(method,))
        mod = make_module(name="myapp.services", classes=(cls,))

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.modules["myapp.services"] = mod

        result = list(cb.iter_functions())
        assert method in result

    def test_module_functions_and_methods(self) -> None:
        func = make_function(name="main", module_name="myapp.core")
        method = make_method(name="run", class_name="App", module_name="myapp.core")
        cls = make_class(name="App", module_name="myapp.core", methods=(method,))
        mod = make_module(name="myapp.core", functions=(func,), classes=(cls,))

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.modules["myapp.core"] = mod

        result = list(cb.iter_functions())
        assert set(result) == {func, method}


class TestCodebaseAddModule:
    """Tests for Codebase.add_module method."""

    def test_add_module(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        mod = make_module(name="myapp.core")

        cb.add_module(mod)

        assert cb.modules["myapp.core"] == mod

    def test_add_duplicate_module_raises(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        mod1 = make_module(name="myapp.core")
        mod2 = make_module(name="myapp.core")

        cb.add_module(mod1)

        with pytest.raises(ValueError, match="module 'myapp.core' already exists"):
            cb.add_module(mod2)

    def test_add_module_invalidates_graphs(self) -> None:
        from archcheck.domain.model.import_graph import ImportGraph

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.set_import_graph(ImportGraph.empty())
        assert cb.has_import_graph()

        cb.add_module(make_module(name="myapp.core"))
        assert not cb.has_import_graph()


class TestCodebaseGraphAccessors:
    """Tests for Codebase graph accessor methods."""

    def test_import_graph_not_set_raises(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        with pytest.raises(ValueError, match="import_graph has not been set"):
            _ = cb.import_graph

    def test_inheritance_graph_not_set_raises(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        with pytest.raises(ValueError, match="inheritance_graph has not been set"):
            _ = cb.inheritance_graph

    def test_call_graph_not_set_raises(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        with pytest.raises(ValueError, match="call_graph has not been set"):
            _ = cb.call_graph

    def test_set_and_get_import_graph(self) -> None:
        from archcheck.domain.model.import_graph import ImportGraph

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        graph = ImportGraph.empty()

        cb.set_import_graph(graph)

        assert cb.import_graph is graph

    def test_set_and_get_inheritance_graph(self) -> None:
        from archcheck.domain.model.inheritance_graph import InheritanceGraph

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        graph = InheritanceGraph.empty()

        cb.set_inheritance_graph(graph)

        assert cb.inheritance_graph is graph

    def test_set_and_get_call_graph(self) -> None:
        from archcheck.domain.model.call_graph import CallGraph

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        graph = CallGraph.empty()

        cb.set_call_graph(graph)

        assert cb.call_graph is graph

    def test_has_import_graph_false(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        assert not cb.has_import_graph()

    def test_has_import_graph_true(self) -> None:
        from archcheck.domain.model.import_graph import ImportGraph

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.set_import_graph(ImportGraph.empty())
        assert cb.has_import_graph()

    def test_has_inheritance_graph_false(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        assert not cb.has_inheritance_graph()

    def test_has_inheritance_graph_true(self) -> None:
        from archcheck.domain.model.inheritance_graph import InheritanceGraph

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.set_inheritance_graph(InheritanceGraph.empty())
        assert cb.has_inheritance_graph()

    def test_has_call_graph_false(self) -> None:
        cb = Codebase(root_path=Path("src"), root_package="myapp")
        assert not cb.has_call_graph()

    def test_has_call_graph_true(self) -> None:
        from archcheck.domain.model.call_graph import CallGraph

        cb = Codebase(root_path=Path("src"), root_package="myapp")
        cb.set_call_graph(CallGraph.empty())
        assert cb.has_call_graph()
