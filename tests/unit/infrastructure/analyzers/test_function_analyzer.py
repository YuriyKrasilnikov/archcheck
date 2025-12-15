"""Tests for infrastructure/analyzers/function_analyzer.py."""

import ast
from pathlib import Path

from archcheck.domain.model.enums import Visibility
from archcheck.infrastructure.analyzers.function_analyzer import FunctionAnalyzer


def get_function_node(code: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Extract function node from code."""
    tree = ast.parse(code)
    node = tree.body[0]
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return node
    raise ValueError("Expected function definition")


class TestFunctionAnalyzerBasic:
    """Tests for basic function analysis."""

    def test_simple_function(self) -> None:
        code = """
def my_function():
    pass
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mypackage.module")

        assert func.name == "my_function"
        assert func.qualified_name == "mypackage.module.my_function"
        assert func.parameters == ()
        assert func.return_annotation is None
        assert func.decorators == ()
        assert func.visibility == Visibility.PUBLIC
        assert func.is_async is False
        assert func.is_generator is False
        assert func.is_method is False

    def test_async_function(self) -> None:
        code = """
async def async_func():
    await something()
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mypackage.module")

        assert func.is_async is True

    def test_generator_function(self) -> None:
        code = """
def gen():
    yield 1
    yield 2
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mypackage.module")

        assert func.is_generator is True

    def test_method(self) -> None:
        code = """
def method(self):
    return self.value
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mypackage.module", "MyClass")

        assert func.name == "method"
        assert func.qualified_name == "mypackage.module.MyClass.method"
        assert func.is_method is True


class TestFunctionAnalyzerVisibility:
    """Tests for visibility detection."""

    def test_public_function(self) -> None:
        code = "def public(): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.visibility == Visibility.PUBLIC

    def test_protected_function(self) -> None:
        code = "def _protected(): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.visibility == Visibility.PROTECTED

    def test_private_function(self) -> None:
        code = "def __private(): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.visibility == Visibility.PRIVATE

    def test_dunder_is_public(self) -> None:
        code = "def __init__(self): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod", "Cls")

        assert func.visibility == Visibility.PUBLIC


class TestFunctionAnalyzerDecorators:
    """Tests for decorator detection."""

    def test_staticmethod(self) -> None:
        code = """
@staticmethod
def static_func():
    pass
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod", "Cls")

        assert func.is_staticmethod is True
        assert func.is_method is True
        assert len(func.decorators) == 1
        assert func.decorators[0].name == "staticmethod"
        assert func.decorators[0].location.file == Path("test.py")

    def test_classmethod(self) -> None:
        code = """
@classmethod
def class_func(cls):
    pass
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod", "Cls")

        assert func.is_classmethod is True
        assert func.is_method is True

    def test_property(self) -> None:
        code = """
@property
def value(self):
    return self._value
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod", "Cls")

        assert func.is_property is True
        assert func.is_method is True

    def test_abstractmethod(self) -> None:
        code = """
@abstractmethod
def abstract_func(self):
    pass
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod", "Cls")

        assert func.is_abstract is True


class TestFunctionAnalyzerParameters:
    """Tests for parameter extraction."""

    def test_no_parameters(self) -> None:
        code = "def func(): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.parameters == ()

    def test_simple_parameters(self) -> None:
        code = "def func(a, b, c): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 3
        assert func.parameters[0].name == "a"
        assert func.parameters[1].name == "b"
        assert func.parameters[2].name == "c"

    def test_parameter_with_annotation(self) -> None:
        code = "def func(x: int): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "x"
        assert func.parameters[0].annotation == "int"

    def test_parameter_with_default(self) -> None:
        code = "def func(x=10): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.parameters[0].default == "10"

    def test_args(self) -> None:
        code = "def func(*args): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "args"
        assert func.parameters[0].is_variadic is True

    def test_kwargs(self) -> None:
        code = "def func(**kwargs): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "kwargs"
        assert func.parameters[0].is_variadic_keyword is True

    def test_keyword_only(self) -> None:
        code = "def func(*, kw_only): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "kw_only"
        assert func.parameters[0].is_keyword_only is True

    def test_positional_only(self) -> None:
        code = "def func(pos_only, /): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "pos_only"
        assert func.parameters[0].is_positional_only is True

    def test_complex_signature(self) -> None:
        code = "def func(pos, /, regular, *args, kw_only, **kwargs): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 5
        assert func.parameters[0].name == "pos"
        assert func.parameters[0].is_positional_only is True
        assert func.parameters[1].name == "regular"
        assert func.parameters[2].name == "args"
        assert func.parameters[2].is_variadic is True
        assert func.parameters[3].name == "kw_only"
        assert func.parameters[3].is_keyword_only is True
        assert func.parameters[4].name == "kwargs"
        assert func.parameters[4].is_variadic_keyword is True

    def test_annotated_args_kwargs(self) -> None:
        code = "def func(*args: int, **kwargs: str): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.parameters[0].annotation == "int"
        assert func.parameters[1].annotation == "str"


class TestFunctionAnalyzerReturnAnnotation:
    """Tests for return annotation extraction."""

    def test_no_return_annotation(self) -> None:
        code = "def func(): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.return_annotation is None

    def test_simple_return_annotation(self) -> None:
        code = "def func() -> int: pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.return_annotation == "int"

    def test_complex_return_annotation(self) -> None:
        code = "def func() -> dict[str, list[int]]: pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.return_annotation == "dict[str, list[int]]"

    def test_none_return_annotation(self) -> None:
        code = "def func() -> None: pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.return_annotation == "None"


class TestFunctionAnalyzerBodyAnalysis:
    """Tests for body analysis integration."""

    def test_body_calls_extracted(self) -> None:
        code = """
def func():
    print("hello")
    helper()
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        # body_calls now contains CallInfo objects, extract callee_names
        call_names = {call.callee_name for call in func.body_calls}
        assert "print" in call_names
        assert "helper" in call_names

    def test_body_attributes_extracted(self) -> None:
        code = """
def func(self):
    return self.value
"""
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod", "Cls")

        assert "self.value" in func.body_attributes


class TestFunctionAnalyzerLocation:
    """Tests for location tracking."""

    def test_function_has_location(self) -> None:
        code = "def func(): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()
        path = Path("test.py")

        func = analyzer.analyze(node, path, "mod")

        assert func.location.file == path
        assert func.location.line == 1


class TestFunctionAnalyzerPurity:
    """Tests for purity_info handling."""

    def test_purity_info_is_none(self) -> None:
        """FunctionAnalyzer does not perform purity analysis."""
        code = "def func(): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert func.purity_info is None


class TestFunctionAnalyzerAdditionalCoverage:
    """Additional tests for full coverage."""

    def test_positional_only_with_default(self) -> None:
        """Test posonly parameter with default value."""
        code = "def func(a, b=10, /): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 2
        assert func.parameters[0].name == "a"
        assert func.parameters[0].default is None
        assert func.parameters[0].is_positional_only is True
        assert func.parameters[1].name == "b"
        assert func.parameters[1].default == "10"
        assert func.parameters[1].is_positional_only is True

    def test_keyword_only_with_default_none(self) -> None:
        """Test keyword-only parameter with None as default."""
        code = "def func(*, kw=None): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "kw"
        assert func.parameters[0].default == "None"
        assert func.parameters[0].is_keyword_only is True

    def test_keyword_only_no_default(self) -> None:
        """Test keyword-only parameter without default."""
        code = "def func(*, required): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "required"
        assert func.parameters[0].default is None
        assert func.parameters[0].is_keyword_only is True

    def test_positional_only_with_annotation(self) -> None:
        """Test positional-only parameter with type annotation."""
        code = "def func(x: int, /): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "x"
        assert func.parameters[0].annotation == "int"
        assert func.parameters[0].is_positional_only is True

    def test_regular_param_with_annotation(self) -> None:
        """Test regular parameter with type annotation."""
        code = "def func(name: str, count: int = 0): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 2
        assert func.parameters[0].name == "name"
        assert func.parameters[0].annotation == "str"
        assert func.parameters[1].name == "count"
        assert func.parameters[1].annotation == "int"
        assert func.parameters[1].default == "0"

    def test_keyword_only_with_annotation(self) -> None:
        """Test keyword-only parameter with type annotation."""
        code = "def func(*, key: str, value: int = 42): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 2
        assert func.parameters[0].name == "key"
        assert func.parameters[0].annotation == "str"
        assert func.parameters[0].is_keyword_only is True
        assert func.parameters[1].name == "value"
        assert func.parameters[1].annotation == "int"
        assert func.parameters[1].default == "42"

    def test_vararg_with_annotation(self) -> None:
        """Test *args with type annotation."""
        code = "def func(*args: int): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "args"
        assert func.parameters[0].annotation == "int"
        assert func.parameters[0].is_variadic is True

    def test_kwarg_with_annotation(self) -> None:
        """Test **kwargs with type annotation."""
        code = "def func(**kwargs: str): pass"
        node = get_function_node(code)
        analyzer = FunctionAnalyzer()

        func = analyzer.analyze(node, Path("test.py"), "mod")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "kwargs"
        assert func.parameters[0].annotation == "str"
        assert func.parameters[0].is_variadic_keyword is True
