"""Tests for infrastructure/analyzers/class_analyzer.py."""

import ast
from pathlib import Path

import pytest

from archcheck.domain.model.enums import Visibility
from archcheck.infrastructure.analyzers.class_analyzer import ClassAnalyzer


def get_class_node(code: str) -> ast.ClassDef:
    """Extract class node from code."""
    tree = ast.parse(code)
    node = tree.body[0]
    if isinstance(node, ast.ClassDef):
        return node
    raise ValueError("Expected class definition")


class TestClassAnalyzerBasic:
    """Tests for basic class analysis."""

    def test_simple_class(self) -> None:
        code = """
class MyClass:
    pass
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mypackage.module")

        assert cls.name == "MyClass"
        assert cls.qualified_name == "mypackage.module.MyClass"
        assert cls.bases == ()
        assert cls.decorators == ()
        assert cls.methods == ()
        assert cls.visibility == Visibility.PUBLIC
        assert cls.is_abstract is False
        assert cls.is_dataclass is False
        assert cls.is_protocol is False
        assert cls.is_exception is False
        assert cls.docstring is None

    def test_class_with_docstring(self) -> None:
        code = '''
class MyClass:
    """This is a docstring."""
    pass
'''
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.docstring == "This is a docstring."


class TestClassAnalyzerVisibility:
    """Tests for visibility detection."""

    def test_public_class(self) -> None:
        code = "class PublicClass: pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.visibility == Visibility.PUBLIC

    def test_protected_class(self) -> None:
        code = "class _ProtectedClass: pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.visibility == Visibility.PROTECTED

    def test_private_class(self) -> None:
        code = "class __PrivateClass: pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.visibility == Visibility.PRIVATE


class TestClassAnalyzerBases:
    """Tests for base class extraction."""

    def test_single_base(self) -> None:
        code = "class Child(Parent): pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.bases == ("Parent",)

    def test_multiple_bases(self) -> None:
        code = "class Child(Base1, Base2, Base3): pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.bases == ("Base1", "Base2", "Base3")

    def test_qualified_base(self) -> None:
        code = "class Child(abc.ABC): pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.bases == ("abc.ABC",)

    def test_generic_base(self) -> None:
        code = "class Container(Generic[T]): pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.bases == ("Generic[T]",)


class TestClassAnalyzerDecorators:
    """Tests for decorator detection."""

    def test_dataclass_decorator(self) -> None:
        code = """
@dataclass
class Data:
    value: int
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.is_dataclass is True
        assert len(cls.decorators) == 1
        assert cls.decorators[0].name == "dataclass"

    def test_dataclass_with_args(self) -> None:
        code = """
@dataclass(frozen=True, slots=True)
class Data:
    value: int
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.is_dataclass is True
        assert cls.decorators[0].arguments == ("frozen=True", "slots=True")


class TestClassAnalyzerAbstract:
    """Tests for abstract class detection."""

    @pytest.mark.parametrize("base", ["ABC", "abc.ABC", "ABCMeta", "abc.ABCMeta"])
    def test_inherits_abc_base(self, base: str) -> None:
        code = f"class Abstract({base}): pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()
        cls = analyzer.analyze(node, Path("test.py"), "mod")
        assert cls.is_abstract is True

    def test_has_abstractmethod(self) -> None:
        code = """
class Abstract:
    @abstractmethod
    def do_something(self):
        pass
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.is_abstract is True

    def test_not_abstract(self) -> None:
        code = "class Concrete: pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.is_abstract is False


class TestClassAnalyzerProtocol:
    """Tests for Protocol detection."""

    def test_inherits_protocol(self) -> None:
        code = "class MyProtocol(Protocol): pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.is_protocol is True

    def test_inherits_typing_protocol(self) -> None:
        code = "class MyProtocol(typing.Protocol): pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.is_protocol is True

    def test_inherits_typing_extensions_protocol(self) -> None:
        code = "class MyProtocol(typing_extensions.Protocol): pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.is_protocol is True


class TestClassAnalyzerException:
    """Tests for exception class detection."""

    @pytest.mark.parametrize(
        "base",
        [
            "Exception",
            "BaseException",
            "RuntimeError",
            "ValueError",
            "TypeError",
            "KeyError",
            "IndexError",
            "AttributeError",
            "OSError",
            "IOError",
            "ImportError",
            "StopIteration",
            "GeneratorExit",
            "SystemExit",
            "KeyboardInterrupt",
        ],
    )
    def test_inherits_exception_base(self, base: str) -> None:
        code = f"class MyError({base}): pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()
        cls = analyzer.analyze(node, Path("test.py"), "mod")
        assert cls.is_exception is True

    def test_not_exception(self) -> None:
        code = "class NotError: pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.is_exception is False


class TestClassAnalyzerMethods:
    """Tests for method extraction."""

    def test_no_methods(self) -> None:
        code = "class Empty: pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.methods == ()

    def test_single_method(self) -> None:
        code = """
class MyClass:
    def method(self):
        pass
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(cls.methods) == 1
        assert cls.methods[0].name == "method"
        assert cls.methods[0].is_method is True
        assert cls.methods[0].qualified_name == "mod.MyClass.method"

    def test_multiple_methods(self) -> None:
        code = """
class MyClass:
    def method1(self):
        pass

    def method2(self):
        pass
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(cls.methods) == 2
        assert cls.methods[0].name == "method1"
        assert cls.methods[1].name == "method2"

    def test_async_method(self) -> None:
        code = """
class MyClass:
    async def async_method(self):
        pass
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(cls.methods) == 1
        assert cls.methods[0].is_async is True

    def test_staticmethod(self) -> None:
        code = """
class MyClass:
    @staticmethod
    def static():
        pass
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(cls.methods) == 1
        assert cls.methods[0].is_staticmethod is True

    def test_classmethod(self) -> None:
        code = """
class MyClass:
    @classmethod
    def from_dict(cls, data):
        pass
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(cls.methods) == 1
        assert cls.methods[0].is_classmethod is True


class TestClassAnalyzerAttributes:
    """Tests for attribute extraction."""

    def test_class_variable(self) -> None:
        code = """
class MyClass:
    class_var = 10
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert "class_var" in cls.attributes

    def test_annotated_class_variable(self) -> None:
        code = """
class MyClass:
    typed_var: int = 10
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert "typed_var" in cls.attributes

    def test_instance_attributes_from_init(self) -> None:
        code = """
class MyClass:
    def __init__(self):
        self.x = 1
        self.y = 2
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert "x" in cls.attributes
        assert "y" in cls.attributes

    def test_combined_attributes(self) -> None:
        code = """
class MyClass:
    class_var = "hello"

    def __init__(self):
        self.instance_var = "world"
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert "class_var" in cls.attributes
        assert "instance_var" in cls.attributes

    def test_attributes_sorted(self) -> None:
        code = """
class MyClass:
    z = 1
    a = 2

    def __init__(self):
        self.m = 3
"""
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        # Attributes should be sorted
        assert cls.attributes == tuple(sorted(cls.attributes))


class TestClassAnalyzerLocation:
    """Tests for location tracking."""

    def test_class_has_location(self) -> None:
        code = "class MyClass: pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()
        path = Path("test.py")

        cls = analyzer.analyze(node, path, "mod")

        assert cls.location.file == path
        assert cls.location.line == 1


class TestClassAnalyzerDIInfo:
    """Tests for DI info handling."""

    def test_di_info_is_none(self) -> None:
        """ClassAnalyzer does not perform DI analysis."""
        code = "class MyClass: pass"
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mod")

        assert cls.di_info is None


class TestClassAnalyzerComplex:
    """Tests for complex class scenarios."""

    def test_full_class(self) -> None:
        code = '''
@dataclass(frozen=True)
class Person:
    """A person entity."""

    DEFAULT_AGE: int = 0

    name: str
    age: int

    def __init__(self, name: str, age: int = 0):
        self.name = name
        self.age = age

    @property
    def is_adult(self) -> bool:
        return self.age >= 18

    @classmethod
    def from_dict(cls, data: dict) -> "Person":
        return cls(**data)

    @staticmethod
    def validate_age(age: int) -> bool:
        return age >= 0
'''
        node = get_class_node(code)
        analyzer = ClassAnalyzer()

        cls = analyzer.analyze(node, Path("test.py"), "mymodule")

        assert cls.name == "Person"
        assert cls.qualified_name == "mymodule.Person"
        assert cls.is_dataclass is True
        assert cls.docstring == "A person entity."
        assert "DEFAULT_AGE" in cls.attributes
        assert "name" in cls.attributes
        assert "age" in cls.attributes
        assert len(cls.methods) == 4  # __init__, is_adult, from_dict, validate_age
        assert cls.decorators[0].arguments == ("frozen=True",)
