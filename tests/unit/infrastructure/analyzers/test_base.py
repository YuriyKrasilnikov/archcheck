"""Tests for infrastructure/analyzers/base.py."""

import ast
from pathlib import Path

import pytest

from archcheck.domain.exceptions.parsing import ASTError, ParsingError
from archcheck.domain.model.enums import Visibility
from archcheck.infrastructure.analyzers.base import (
    compute_module_name,
    extract_base_names,
    extract_init_attributes,
    get_docstring,
    get_visibility,
    has_decorator,
    is_generator,
    make_location,
    resolve_relative_import,
    unparse_node,
)


class TestMakeLocation:
    """Tests for make_location function."""

    def test_valid_node(self) -> None:
        code = "x = 1"
        tree = ast.parse(code)
        node = tree.body[0]
        path = Path("test.py")

        loc = make_location(node, path)

        assert loc.file == path
        assert loc.line == 1
        assert loc.column == 0

    def test_node_without_lineno_raises(self) -> None:
        # Create node without line info
        node = ast.expr()
        path = Path("test.py")

        with pytest.raises(ASTError, match="node has no line info"):
            make_location(node, path)

    def test_with_end_positions(self) -> None:
        code = "variable = 123"
        tree = ast.parse(code)
        node = tree.body[0]
        path = Path("test.py")

        loc = make_location(node, path)

        assert loc.end_line == 1
        assert loc.end_column is not None


class TestGetVisibility:
    """Tests for get_visibility function."""

    def test_public_name(self) -> None:
        assert get_visibility("my_function") == Visibility.PUBLIC
        assert get_visibility("MyClass") == Visibility.PUBLIC
        assert get_visibility("name") == Visibility.PUBLIC

    def test_protected_name(self) -> None:
        assert get_visibility("_helper") == Visibility.PROTECTED
        assert get_visibility("_internal") == Visibility.PROTECTED

    def test_private_name(self) -> None:
        assert get_visibility("__secret") == Visibility.PRIVATE
        assert get_visibility("__mangled_name") == Visibility.PRIVATE

    def test_dunder_is_public(self) -> None:
        # __init__, __str__ etc are public
        assert get_visibility("__init__") == Visibility.PUBLIC
        assert get_visibility("__str__") == Visibility.PUBLIC
        assert get_visibility("__eq__") == Visibility.PUBLIC


class TestComputeModuleName:
    """Tests for compute_module_name function."""

    def test_simple_module(self) -> None:
        file_path = Path("/project/src/mymodule.py")
        root_path = Path("/project/src")

        name = compute_module_name(file_path, root_path)
        assert name == "mymodule"

    def test_nested_module(self) -> None:
        file_path = Path("/project/src/package/subpackage/module.py")
        root_path = Path("/project/src")

        name = compute_module_name(file_path, root_path)
        assert name == "package.subpackage.module"

    def test_init_file(self) -> None:
        file_path = Path("/project/src/package/__init__.py")
        root_path = Path("/project/src")

        name = compute_module_name(file_path, root_path)
        assert name == "package"

    def test_nested_init_file(self) -> None:
        file_path = Path("/project/src/package/sub/__init__.py")
        root_path = Path("/project/src")

        name = compute_module_name(file_path, root_path)
        assert name == "package.sub"

    def test_file_not_under_root_raises(self) -> None:
        file_path = Path("/other/location/module.py")
        root_path = Path("/project/src")

        with pytest.raises(ParsingError, match="not under"):
            compute_module_name(file_path, root_path)

    def test_invalid_identifier_raises(self) -> None:
        file_path = Path("/project/src/123invalid.py")
        root_path = Path("/project/src")

        with pytest.raises(ParsingError, match="not valid Python identifier"):
            compute_module_name(file_path, root_path)

    def test_root_init_raises(self) -> None:
        # __init__.py at root level results in empty name
        file_path = Path("/project/src/__init__.py")
        root_path = Path("/project/src")

        with pytest.raises(ParsingError, match="cannot determine module name"):
            compute_module_name(file_path, root_path)


class TestResolveRelativeImport:
    """Tests for resolve_relative_import function."""

    def test_absolute_import(self) -> None:
        result = resolve_relative_import("os.path", 0, "mypackage.module")
        assert result == "os.path"

    def test_absolute_import_none_module_raises(self) -> None:
        with pytest.raises(ValueError, match="absolute import must have module"):
            resolve_relative_import(None, 0, "mypackage.module")

    def test_single_dot_import(self) -> None:
        # from . import something
        result = resolve_relative_import("sibling", 1, "mypackage.module")
        assert result == "mypackage.sibling"

    def test_single_dot_import_no_module(self) -> None:
        # from . import something (module is None after dots)
        result = resolve_relative_import(None, 1, "mypackage.module")
        assert result == "mypackage"

    def test_double_dot_import(self) -> None:
        # from .. import something
        result = resolve_relative_import("parent", 2, "mypackage.sub.module")
        assert result == "mypackage.parent"

    def test_double_dot_no_module(self) -> None:
        result = resolve_relative_import(None, 2, "mypackage.sub.module")
        assert result == "mypackage"

    def test_triple_dot_import(self) -> None:
        result = resolve_relative_import("other", 3, "a.b.c.d")
        assert result == "a.other"

    def test_level_exceeds_depth_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds package depth"):
            resolve_relative_import("x", 3, "package.module")

    def test_relative_results_empty_raises(self) -> None:
        # Single level module with level 1 and no module part
        with pytest.raises(ValueError, match="results in empty module"):
            resolve_relative_import(None, 1, "single")


class TestUnparseNode:
    """Tests for unparse_node function."""

    def test_simple_name(self) -> None:
        node = ast.parse("x", mode="eval").body
        assert unparse_node(node) == "x"

    def test_attribute(self) -> None:
        node = ast.parse("os.path", mode="eval").body
        assert unparse_node(node) == "os.path"

    def test_call(self) -> None:
        node = ast.parse("func(a, b)", mode="eval").body
        assert unparse_node(node) == "func(a, b)"

    def test_subscript(self) -> None:
        node = ast.parse("list[int]", mode="eval").body
        assert unparse_node(node) == "list[int]"


class TestIsGenerator:
    """Tests for is_generator function."""

    def test_regular_function(self) -> None:
        code = """
def func():
    return 1
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert is_generator(func_node) is False

    def test_generator_with_yield(self) -> None:
        code = """
def gen():
    yield 1
    yield 2
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert is_generator(func_node) is True

    def test_generator_with_yield_from(self) -> None:
        code = """
def gen():
    yield from range(10)
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert is_generator(func_node) is True

    def test_nested_function_yield_not_generator(self) -> None:
        """Parent function with nested generator is NOT a generator."""
        code = """
def outer():
    def inner():
        yield 1
    return inner
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert is_generator(func_node) is False

    def test_nested_async_function_yield_not_generator(self) -> None:
        code = """
def outer():
    async def inner():
        yield 1
    return inner
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert is_generator(func_node) is False

    def test_nested_class_yield_not_generator(self) -> None:
        code = """
def outer():
    class Inner:
        def method(self):
            yield 1
    return Inner
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert is_generator(func_node) is False

    def test_lambda_yield_not_counted(self) -> None:
        # Note: lambda can't actually have yield, but we test the visitor path
        code = """
def outer():
    f = lambda x: x
    return f
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)
        assert is_generator(func_node) is False

    def test_async_generator(self) -> None:
        code = """
async def agen():
    yield 1
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.AsyncFunctionDef)
        assert is_generator(func_node) is True


class TestExtractInitAttributes:
    """Tests for extract_init_attributes function."""

    def test_simple_assignments(self) -> None:
        code = """
def __init__(self):
    self.x = 1
    self.y = 2
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.FunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"x", "y"})

    def test_annotated_assignment(self) -> None:
        code = """
def __init__(self):
    self.value: int = 42
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.FunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"value"})

    def test_augmented_assignment(self) -> None:
        code = """
def __init__(self):
    self.count = 0
    self.count += 1
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.FunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"count"})

    def test_walrus_operator(self) -> None:
        # Note: walrus operator cannot be used directly with self.x (Python limitation)
        # But we can test walrus for local variables within conditions
        code = """
def __init__(self):
    if (data := get_data()):
        self.data = data
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.FunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"data"})

    def test_nested_function_ignored(self) -> None:
        code = """
def __init__(self):
    self.x = 1
    def helper():
        self.y = 2  # This is different self!
    helper()
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.FunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"x"})  # y not included

    def test_nested_class_ignored(self) -> None:
        code = """
def __init__(self):
    self.x = 1
    class Inner:
        def __init__(inner_self):
            inner_self.y = 2
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.FunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"x"})

    def test_nested_async_function_ignored(self) -> None:
        code = """
def __init__(self):
    self.x = 1
    async def async_helper():
        self.y = 2
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.FunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"x"})

    def test_lambda_ignored(self) -> None:
        code = """
def __init__(self):
    self.x = 1
    f = lambda: None
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.FunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"x"})

    def test_annotated_without_value_ignored(self) -> None:
        code = """
def __init__(self):
    self.x: int  # No value, not an assignment
    self.y: str = "hello"
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.FunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"y"})  # x not included

    def test_async_init_attributes(self) -> None:
        """Test extract_init_attributes with async function."""
        code = """
async def __init__(self):
    self.x = 1
    self.y = await get_value()
"""
        tree = ast.parse(code)
        init_node = tree.body[0]
        assert isinstance(init_node, ast.AsyncFunctionDef)

        attrs = extract_init_attributes(init_node)
        assert attrs == frozenset({"x", "y"})


class TestExtractBaseNames:
    """Tests for extract_base_names function."""

    def test_no_bases(self) -> None:
        code = "class Foo: pass"
        tree = ast.parse(code)
        class_node = tree.body[0]
        assert isinstance(class_node, ast.ClassDef)

        bases = extract_base_names(class_node)
        assert bases == ()

    def test_single_base(self) -> None:
        code = "class Foo(Bar): pass"
        tree = ast.parse(code)
        class_node = tree.body[0]
        assert isinstance(class_node, ast.ClassDef)

        bases = extract_base_names(class_node)
        assert bases == ("Bar",)

    def test_multiple_bases(self) -> None:
        code = "class Foo(Bar, Baz): pass"
        tree = ast.parse(code)
        class_node = tree.body[0]
        assert isinstance(class_node, ast.ClassDef)

        bases = extract_base_names(class_node)
        assert bases == ("Bar", "Baz")

    def test_qualified_base(self) -> None:
        code = "class Foo(abc.ABC): pass"
        tree = ast.parse(code)
        class_node = tree.body[0]
        assert isinstance(class_node, ast.ClassDef)

        bases = extract_base_names(class_node)
        assert bases == ("abc.ABC",)

    def test_generic_base(self) -> None:
        code = "class Foo(Generic[T]): pass"
        tree = ast.parse(code)
        class_node = tree.body[0]
        assert isinstance(class_node, ast.ClassDef)

        bases = extract_base_names(class_node)
        assert bases == ("Generic[T]",)


class TestHasDecorator:
    """Tests for has_decorator function."""

    def test_no_decorators(self) -> None:
        code = "def foo(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)

        assert has_decorator(func_node.decorator_list, "staticmethod") is False

    def test_simple_decorator(self) -> None:
        code = "@staticmethod\ndef foo(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)

        assert has_decorator(func_node.decorator_list, "staticmethod") is True
        assert has_decorator(func_node.decorator_list, "classmethod") is False

    def test_decorator_with_args(self) -> None:
        code = "@dataclass(frozen=True)\nclass Foo: pass"
        tree = ast.parse(code)
        class_node = tree.body[0]
        assert isinstance(class_node, ast.ClassDef)

        assert has_decorator(class_node.decorator_list, "dataclass") is True

    def test_qualified_decorator(self) -> None:
        code = "@abc.abstractmethod\ndef foo(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)

        assert has_decorator(func_node.decorator_list, "abstractmethod") is True

    def test_qualified_decorator_with_args(self) -> None:
        code = "@pytest.fixture(scope='module')\ndef foo(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        assert isinstance(func_node, ast.FunctionDef)

        assert has_decorator(func_node.decorator_list, "fixture") is True


class TestGetDocstring:
    """Tests for get_docstring function."""

    def test_function_docstring(self) -> None:
        code = '''
def foo():
    """This is a docstring."""
    pass
'''
        tree = ast.parse(code)
        func_node = tree.body[0]

        docstring = get_docstring(func_node)
        assert docstring == "This is a docstring."

    def test_class_docstring(self) -> None:
        code = '''
class Foo:
    """Class docstring."""
    pass
'''
        tree = ast.parse(code)
        class_node = tree.body[0]

        docstring = get_docstring(class_node)
        assert docstring == "Class docstring."

    def test_module_docstring(self) -> None:
        code = '''"""Module docstring."""

x = 1
'''
        tree = ast.parse(code)

        docstring = get_docstring(tree)
        assert docstring == "Module docstring."

    def test_no_docstring(self) -> None:
        code = "def foo(): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]

        docstring = get_docstring(func_node)
        assert docstring is None

    def test_docstring_whitespace_cleaned(self) -> None:
        """Test that clean=True removes indentation and normalizes whitespace."""
        code = '''
def foo():
    """
    This is a docstring
    with multiple lines
    and indentation.
    """
    pass
'''
        tree = ast.parse(code)
        func_node = tree.body[0]

        docstring = get_docstring(func_node)

        # clean=True should remove leading/trailing whitespace and normalize indentation
        assert docstring is not None
        assert not docstring.startswith("\n")
        assert not docstring.startswith("    ")
        assert "This is a docstring" in docstring
