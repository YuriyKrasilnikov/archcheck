"""Tests for infrastructure/analyzers/decorator_analyzer.py."""

import ast
from pathlib import Path

from archcheck.infrastructure.analyzers.decorator_analyzer import DecoratorAnalyzer


def get_decorators(code: str) -> list[ast.expr]:
    """Extract decorator list from code."""
    tree = ast.parse(code)
    node = tree.body[0]
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return node.decorator_list
    raise ValueError("Expected function or class definition")


class TestDecoratorAnalyzerSimple:
    """Tests for simple decorator extraction."""

    def test_no_decorators(self) -> None:
        code = "def foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert result == ()

    def test_simple_name_decorator(self) -> None:
        code = "@staticmethod\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].name == "staticmethod"
        assert result[0].arguments == ()
        assert result[0].location is not None

    def test_multiple_decorators(self) -> None:
        code = """
@decorator1
@decorator2
def foo(): pass
"""
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 2
        assert result[0].name == "decorator1"
        assert result[1].name == "decorator2"


class TestDecoratorAnalyzerAttribute:
    """Tests for attribute (qualified) decorators."""

    def test_qualified_decorator(self) -> None:
        code = "@abc.abstractmethod\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].name == "abc.abstractmethod"
        assert result[0].arguments == ()

    def test_deeply_qualified_decorator(self) -> None:
        code = "@package.module.decorator\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].name == "package.module.decorator"


class TestDecoratorAnalyzerCall:
    """Tests for decorator calls with arguments."""

    def test_decorator_with_no_args(self) -> None:
        code = "@decorator()\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].name == "decorator"
        assert result[0].arguments == ()

    def test_decorator_with_positional_args(self) -> None:
        code = "@decorator('arg1', 42)\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].name == "decorator"
        assert result[0].arguments == ("'arg1'", "42")

    def test_decorator_with_keyword_args(self) -> None:
        code = "@dataclass(frozen=True, slots=True)\nclass Foo: pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].name == "dataclass"
        assert result[0].arguments == ("frozen=True", "slots=True")

    def test_decorator_with_mixed_args(self) -> None:
        code = "@decorator('name', value=123)\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].arguments == ("'name'", "value=123")

    def test_qualified_decorator_with_args(self) -> None:
        code = "@pytest.fixture(scope='module')\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].name == "pytest.fixture"
        assert result[0].arguments == ("scope='module'",)


class TestDecoratorAnalyzerComplex:
    """Tests for complex decorator expressions."""

    def test_decorator_with_kwargs_unpacking(self) -> None:
        code = "@decorator(**options)\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].arguments == ("**options",)

    def test_class_decorators(self) -> None:
        code = """
@dataclass(frozen=True)
@total_ordering
class Foo:
    pass
"""
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 2
        assert result[0].name == "dataclass"
        assert result[0].arguments == ("frozen=True",)
        assert result[1].name == "total_ordering"
        assert result[1].arguments == ()


class TestDecoratorAnalyzerLocation:
    """Tests for decorator location tracking."""

    def test_decorator_has_location(self) -> None:
        code = "@my_decorator\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()
        path = Path("test.py")

        result = analyzer.analyze(decorators, path)

        assert len(result) == 1
        assert result[0].location is not None
        assert result[0].location.file == path
        assert result[0].location.line == 1

    def test_multiple_decorators_locations(self) -> None:
        code = """@dec1
@dec2
def foo(): pass
"""
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 2
        assert result[0].location is not None
        assert result[1].location is not None
        assert result[0].location.line == 1
        assert result[1].location.line == 2


class TestDecoratorAnalyzerEdgeCases:
    """Tests for edge cases and full coverage."""

    def test_complex_expression_decorator(self) -> None:
        """Test decorator that is a complex expression (not name/attr/call)."""
        code = "@decorators[0]\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].name == "decorators[0]"
        assert result[0].arguments == ()

    def test_call_with_subscript_func(self) -> None:
        """Test decorator call where func is subscript."""
        code = "@decorators[0](arg)\ndef foo(): pass"
        decorators = get_decorators(code)
        analyzer = DecoratorAnalyzer()

        result = analyzer.analyze(decorators, Path("test.py"))

        assert len(result) == 1
        assert result[0].name == "decorators[0]"
        assert result[0].arguments == ("arg",)
