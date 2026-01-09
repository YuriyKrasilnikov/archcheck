"""Tests for function_analyzer.

Tests:
- Simple function
- Async function
- Generator function
- Method
- Parameters (all kinds)
- Return annotation
- Decorators
- Body calls extraction
"""

import ast

from archcheck.domain.codebase import ParameterKind
from archcheck.infrastructure.analyzers.function_analyzer import analyze_function


class TestAnalyzeFunction:
    """Tests for analyze_function()."""

    def test_simple_function(self) -> None:
        """Def foo(): pass."""
        code = "def foo(): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "app.service")

        assert func.name == "foo"
        assert func.qualified_name == "app.service.foo"
        assert func.is_async is False
        assert func.is_generator is False
        assert func.is_method is False

    def test_async_function(self) -> None:
        """Async def fetch(): pass."""
        code = "async def fetch(): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.AsyncFunctionDef)

        func = analyze_function(node, "app.api")

        assert func.name == "fetch"
        assert func.is_async is True

    def test_generator_function(self) -> None:
        """Def items(): yield 1."""
        code = "def items(): yield 1"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "app.iter")

        assert func.is_generator is True

    def test_method(self) -> None:
        """Method in class."""
        code = """
class Service:
    def process(self): pass
"""
        tree = ast.parse(code)
        class_node = tree.body[0]
        assert isinstance(class_node, ast.ClassDef)
        method_node = class_node.body[0]
        assert isinstance(method_node, ast.FunctionDef)

        func = analyze_function(method_node, "app.service", class_name="Service")

        assert func.name == "process"
        assert func.qualified_name == "app.service.Service.process"
        assert func.is_method is True

    def test_positional_or_keyword_param(self) -> None:
        """Def f(x): pass."""
        code = "def f(x): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "x"
        assert func.parameters[0].kind == ParameterKind.POSITIONAL_OR_KEYWORD

    def test_positional_only_param(self) -> None:
        """Def f(x, /): pass."""
        code = "def f(x, /): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert len(func.parameters) == 1
        assert func.parameters[0].kind == ParameterKind.POSITIONAL_ONLY

    def test_var_positional_param(self) -> None:
        """Def f(*args): pass."""
        code = "def f(*args): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "args"
        assert func.parameters[0].kind == ParameterKind.VAR_POSITIONAL

    def test_keyword_only_param(self) -> None:
        """Def f(*, x): pass."""
        code = "def f(*, x): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert len(func.parameters) == 1
        assert func.parameters[0].kind == ParameterKind.KEYWORD_ONLY

    def test_var_keyword_param(self) -> None:
        """Def f(**kwargs): pass."""
        code = "def f(**kwargs): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert len(func.parameters) == 1
        assert func.parameters[0].name == "kwargs"
        assert func.parameters[0].kind == ParameterKind.VAR_KEYWORD

    def test_param_with_annotation(self) -> None:
        """Def f(x: int): pass."""
        code = "def f(x: int): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert func.parameters[0].annotation == "int"

    def test_param_with_default(self) -> None:
        """Def f(x=10): pass."""
        code = "def f(x=10): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert func.parameters[0].default == "10"

    def test_return_annotation(self) -> None:
        """Def f() -> int: pass."""
        code = "def f() -> int: pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert func.return_annotation == "int"

    def test_complex_annotation(self) -> None:
        """Def f(x: str | None) -> list[int]: pass."""
        code = "def f(x: str | None) -> list[int]: pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert func.parameters[0].annotation == "str | None"
        assert func.return_annotation == "list[int]"

    def test_decorators(self) -> None:
        r"""@route\n@auth\ndef f(): pass."""
        code = "@route\n@auth\ndef f(): pass"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert func.decorators == ("route", "auth")

    def test_decorator_with_args(self) -> None:
        r"""@route("/api")\ndef f(): pass."""
        code = '@route("/api")\ndef f(): pass'
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert func.decorators == ("route('/api')",)

    def test_body_calls_simple(self) -> None:
        """Def f(): foo()."""
        code = "def f(): foo()"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert "foo" in func.body_calls

    def test_body_calls_attribute(self) -> None:
        """Def f(): self.process()."""
        code = "def f(): self.process()"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert "self.process" in func.body_calls

    def test_body_calls_multiple(self) -> None:
        """Def f(): foo(); bar()."""
        code = "def f():\n    foo()\n    bar()"
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "test")

        assert "foo" in func.body_calls
        assert "bar" in func.body_calls

    def test_full_function(self) -> None:
        """Complex function with all features."""
        code = """
@decorator
def process(x: int, y: str = "default", *, z: bool = True, **kwargs) -> dict:
    result = helper()
    self.log()
    return {"x": x}
"""
        tree = ast.parse(code)
        node = tree.body[0]
        assert isinstance(node, ast.FunctionDef)

        func = analyze_function(node, "app.service")

        assert func.name == "process"
        assert func.qualified_name == "app.service.process"
        assert len(func.parameters) == 4
        assert func.parameters[0].name == "x"
        assert func.parameters[1].default == "'default'"
        assert func.parameters[2].kind == ParameterKind.KEYWORD_ONLY
        assert func.parameters[3].kind == ParameterKind.VAR_KEYWORD
        assert func.return_annotation == "dict"
        assert "decorator" in func.decorators
        assert "helper" in func.body_calls
        assert "self.log" in func.body_calls
