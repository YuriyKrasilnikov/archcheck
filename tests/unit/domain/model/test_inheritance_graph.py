"""Tests for domain/model/inheritance_graph.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.class_ import Class
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.inheritance_graph import InheritanceGraph
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_class(
    name: str,
    module_name: str,
    bases: tuple[str, ...] = (),
) -> Class:
    """Create a valid Class for tests."""
    return Class(
        name=name,
        qualified_name=f"{module_name}.{name}",
        bases=bases,
        decorators=(),
        methods=(),
        attributes=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
    )


def make_module(name: str, classes: tuple[Class, ...] = ()) -> Module:
    """Create a valid Module with classes."""
    return Module(
        name=name,
        path=Path(f"src/{name.replace('.', '/')}.py"),
        imports=(),
        classes=classes,
        functions=(),
        constants=(),
    )


class TestInheritanceGraphCreation:
    """Tests for valid InheritanceGraph creation."""

    def test_empty_graph(self) -> None:
        g = InheritanceGraph.empty()
        assert g.class_count == 0
        assert g.inheritance_count == 0

    def test_is_frozen(self) -> None:
        g = InheritanceGraph.empty()
        with pytest.raises(AttributeError):
            g.graph = None  # type: ignore[misc]


class TestInheritanceGraphFromModules:
    """Tests for InheritanceGraph.from_modules class method."""

    def test_empty_modules(self) -> None:
        g = InheritanceGraph.from_modules({})
        assert g.class_count == 0

    def test_class_without_bases(self) -> None:
        cls = make_class("MyClass", "myapp.core")
        mod = make_module("myapp.core", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp.core": mod})
        # Class without bases is not in graph (no edges)
        assert g.bases_of("myapp.core.MyClass") == frozenset()

    def test_class_with_single_base(self) -> None:
        cls = make_class("Child", "myapp.core", bases=("Parent",))
        mod = make_module("myapp.core", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp.core": mod})
        assert g.has_base("myapp.core.Child", "Parent")

    def test_class_with_multiple_bases(self) -> None:
        cls = make_class("Child", "myapp.core", bases=("Base1", "Base2"))
        mod = make_module("myapp.core", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp.core": mod})
        assert g.bases_of("myapp.core.Child") == frozenset({"Base1", "Base2"})

    def test_qualified_base_name(self) -> None:
        cls = make_class("MyClass", "myapp.core", bases=("abc.ABC",))
        mod = make_module("myapp.core", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp.core": mod})
        assert g.has_base("myapp.core.MyClass", "abc.ABC")


class TestInheritanceGraphBasesOf:
    """Tests for InheritanceGraph.bases_of method."""

    def test_class_with_bases(self) -> None:
        cls = make_class("Child", "myapp", bases=("Parent", "Mixin"))
        mod = make_module("myapp", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp": mod})
        assert g.bases_of("myapp.Child") == frozenset({"Parent", "Mixin"})

    def test_class_without_bases(self) -> None:
        cls = make_class("Standalone", "myapp")
        mod = make_module("myapp", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp": mod})
        assert g.bases_of("myapp.Standalone") == frozenset()

    def test_nonexistent_class(self) -> None:
        g = InheritanceGraph.empty()
        assert g.bases_of("unknown.Class") == frozenset()


class TestInheritanceGraphSubclassesOf:
    """Tests for InheritanceGraph.subclasses_of method."""

    def test_base_with_subclasses(self) -> None:
        child1 = make_class("Child1", "myapp", bases=("BaseClass",))
        child2 = make_class("Child2", "myapp", bases=("BaseClass",))
        mod = make_module("myapp", classes=(child1, child2))
        g = InheritanceGraph.from_modules({"myapp": mod})
        assert g.subclasses_of("BaseClass") == frozenset(
            {
                "myapp.Child1",
                "myapp.Child2",
            }
        )

    def test_base_without_subclasses(self) -> None:
        cls = make_class("Standalone", "myapp")
        mod = make_module("myapp", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp": mod})
        assert g.subclasses_of("Standalone") == frozenset()

    def test_nonexistent_base(self) -> None:
        g = InheritanceGraph.empty()
        assert g.subclasses_of("Unknown") == frozenset()


class TestInheritanceGraphHasBase:
    """Tests for InheritanceGraph.has_base method."""

    def test_existing_inheritance(self) -> None:
        cls = make_class("Child", "myapp", bases=("Parent",))
        mod = make_module("myapp", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp": mod})
        assert g.has_base("myapp.Child", "Parent")

    def test_nonexistent_inheritance(self) -> None:
        cls = make_class("Child", "myapp", bases=("Parent",))
        mod = make_module("myapp", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp": mod})
        assert not g.has_base("myapp.Child", "Other")


class TestInheritanceGraphHasClass:
    """Tests for InheritanceGraph.has_class method."""

    def test_class_with_base(self) -> None:
        cls = make_class("Child", "myapp", bases=("Parent",))
        mod = make_module("myapp", classes=(cls,))
        g = InheritanceGraph.from_modules({"myapp": mod})
        assert g.has_class("myapp.Child")
        assert g.has_class("Parent")  # Base is also in graph

    def test_nonexistent_class(self) -> None:
        g = InheritanceGraph.empty()
        assert not g.has_class("Unknown")


class TestInheritanceGraphCounts:
    """Tests for InheritanceGraph count properties."""

    def test_class_count(self) -> None:
        child = make_class("Child", "myapp", bases=("Parent",))
        mod = make_module("myapp", classes=(child,))
        g = InheritanceGraph.from_modules({"myapp": mod})
        # Both Child and Parent are nodes
        assert g.class_count == 2

    def test_inheritance_count(self) -> None:
        child = make_class("Child", "myapp", bases=("Base1", "Base2"))
        mod = make_module("myapp", classes=(child,))
        g = InheritanceGraph.from_modules({"myapp": mod})
        assert g.inheritance_count == 2

    def test_classes_property(self) -> None:
        child = make_class("Child", "myapp", bases=("Parent",))
        mod = make_module("myapp", classes=(child,))
        g = InheritanceGraph.from_modules({"myapp": mod})
        assert "myapp.Child" in g.classes
        assert "Parent" in g.classes
