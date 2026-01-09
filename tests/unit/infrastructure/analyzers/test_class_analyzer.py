"""Tests for class_analyzer.

Tests:
- Simple class
- Class with bases
- Class with methods
- Protocol detection
- Dataclass detection
"""

import ast

from archcheck.infrastructure.analyzers.class_analyzer import analyze_class


class TestAnalyzeClass:
    """Tests for analyze_class()."""

    def test_simple_class(self) -> None:
        """Class Foo: pass."""
        code = "class Foo: pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.models")

        assert cls.name == "Foo"
        assert cls.qualified_name == "app.models.Foo"
        assert cls.bases == ()
        assert cls.methods == ()
        assert cls.is_protocol is False
        assert cls.is_dataclass is False

    def test_class_with_single_base(self) -> None:
        """Class User(BaseModel): pass."""
        code = "class User(BaseModel): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.models")

        assert cls.bases == ("BaseModel",)

    def test_class_with_multiple_bases(self) -> None:
        """Class User(BaseModel, Mixin): pass."""
        code = "class User(BaseModel, Mixin): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.models")

        assert cls.bases == ("BaseModel", "Mixin")

    def test_class_with_dotted_base(self) -> None:
        """Class User(pydantic.BaseModel): pass."""
        code = "class User(pydantic.BaseModel): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.models")

        assert cls.bases == ("pydantic.BaseModel",)

    def test_class_with_method(self) -> None:
        """Class Service: def process(self): pass."""
        code = """
class Service:
    def process(self):
        pass
"""
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.service")

        assert len(cls.methods) == 1
        assert cls.methods[0].name == "process"
        assert cls.methods[0].is_method is True

    def test_class_with_multiple_methods(self) -> None:
        """Class with multiple methods."""
        code = """
class Service:
    def __init__(self):
        pass
    def process(self):
        pass
    async def fetch(self):
        pass
"""
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.service")

        assert len(cls.methods) == 3
        assert cls.methods[0].name == "__init__"
        assert cls.methods[1].name == "process"
        assert cls.methods[2].name == "fetch"
        assert cls.methods[2].is_async is True

    def test_protocol_simple(self) -> None:
        """Class Repository(Protocol): pass."""
        code = "class Repository(Protocol): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.ports")

        assert cls.is_protocol is True

    def test_protocol_typing(self) -> None:
        """Class Repository(typing.Protocol): pass."""
        code = "class Repository(typing.Protocol): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.ports")

        assert cls.is_protocol is True

    def test_protocol_with_other_bases(self) -> None:
        """Class Repository(Protocol, OtherBase): pass."""
        code = "class Repository(Protocol, OtherBase): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.ports")

        assert cls.is_protocol is True

    def test_dataclass_simple(self) -> None:
        """@dataclass class User: pass."""
        code = "@dataclass\nclass User: pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.dto")

        assert cls.is_dataclass is True

    def test_dataclass_with_args(self) -> None:
        """@dataclass(frozen=True) class User: pass."""
        code = "@dataclass(frozen=True)\nclass User: pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.dto")

        assert cls.is_dataclass is True

    def test_dataclass_empty_args(self) -> None:
        """@dataclass() class User: pass."""
        code = "@dataclass()\nclass User: pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.dto")

        assert cls.is_dataclass is True

    def test_dataclass_module_prefix(self) -> None:
        """@dataclasses.dataclass class User: pass."""
        code = "@dataclasses.dataclass\nclass User: pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.dto")

        assert cls.is_dataclass is True

    def test_dataclass_module_prefix_with_args(self) -> None:
        """@dataclasses.dataclass(frozen=True) class User: pass."""
        code = "@dataclasses.dataclass(frozen=True)\nclass User: pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.dto")

        assert cls.is_dataclass is True

    def test_not_dataclass(self) -> None:
        """@other_decorator class User: pass."""
        code = "@other_decorator\nclass User: pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.dto")

        assert cls.is_dataclass is False

    def test_method_qualified_name(self) -> None:
        """Method qualified_name includes class."""
        code = """
class Service:
    def process(self):
        pass
"""
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.ClassDef)

        cls = analyze_class(node, "app.service")

        assert cls.methods[0].qualified_name == "app.service.Service.process"
