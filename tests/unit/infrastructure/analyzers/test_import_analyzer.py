"""Tests for infrastructure/analyzers/import_analyzer.py."""

import ast
from pathlib import Path

from archcheck.infrastructure.analyzers.import_analyzer import ImportAnalyzer


def make_tree(code: str) -> ast.Module:
    """Parse code into AST module."""
    return ast.parse(code)


class TestImportAnalyzerBasic:
    """Tests for basic import extraction."""

    def test_simple_import(self) -> None:
        code = "import os"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        imp = imports[0]
        assert imp.module == "os"
        assert imp.name is None
        assert imp.alias is None
        assert imp.level == 0
        assert imp.is_type_checking is False
        assert imp.is_conditional is False
        assert imp.is_lazy is False

    def test_import_with_alias(self) -> None:
        code = "import numpy as np"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        assert imports[0].module == "numpy"
        assert imports[0].alias == "np"

    def test_multiple_imports(self) -> None:
        code = "import os, sys"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 2
        assert imports[0].module == "os"
        assert imports[1].module == "sys"

    def test_from_import(self) -> None:
        code = "from os import path"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        imp = imports[0]
        assert imp.module == "os"
        assert imp.name == "path"
        assert imp.alias is None

    def test_from_import_with_alias(self) -> None:
        code = "from pathlib import Path as P"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        imp = imports[0]
        assert imp.module == "pathlib"
        assert imp.name == "Path"
        assert imp.alias == "P"

    def test_from_import_multiple(self) -> None:
        code = "from os import path, getcwd, chdir"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 3
        assert imports[0].name == "path"
        assert imports[1].name == "getcwd"
        assert imports[2].name == "chdir"

    def test_star_import(self) -> None:
        code = "from os import *"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        assert imports[0].name == "*"


class TestImportAnalyzerRelative:
    """Tests for relative import handling."""

    def test_single_dot_import(self) -> None:
        code = "from . import sibling"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.subpackage.module")

        assert len(imports) == 1
        imp = imports[0]
        assert imp.module == "mypackage.subpackage"
        assert imp.name == "sibling"
        assert imp.level == 1

    def test_single_dot_import_with_module(self) -> None:
        code = "from .utils import helper"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.subpackage.module")

        assert len(imports) == 1
        imp = imports[0]
        assert imp.module == "mypackage.subpackage.utils"
        assert imp.name == "helper"
        assert imp.level == 1

    def test_double_dot_import(self) -> None:
        code = "from ..parent import something"
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.sub.deep.module")

        assert len(imports) == 1
        imp = imports[0]
        assert imp.module == "mypackage.sub.parent"
        assert imp.name == "something"
        assert imp.level == 2


class TestImportAnalyzerTypeChecking:
    """Tests for TYPE_CHECKING block handling."""

    def test_type_checking_import(self) -> None:
        code = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypackage import MyClass
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 2
        # First import is TYPE_CHECKING itself
        assert imports[0].module == "typing"
        assert imports[0].is_type_checking is False

        # Second import is inside TYPE_CHECKING
        assert imports[1].module == "mypackage"
        assert imports[1].is_type_checking is True

    def test_typing_type_checking(self) -> None:
        code = """
import typing

if typing.TYPE_CHECKING:
    from mypackage import MyClass
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        # typing import + MyClass import
        assert len(imports) == 2
        assert imports[1].is_type_checking is True


class TestImportAnalyzerConditional:
    """Tests for conditional import handling."""

    def test_if_block_import(self) -> None:
        code = """
if sys.platform == 'win32':
    import winreg
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        assert imports[0].module == "winreg"
        assert imports[0].is_conditional is True

    def test_try_block_import(self) -> None:
        code = """
try:
    import ujson as json
except ImportError:
    import json
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 2
        assert imports[0].module == "ujson"
        assert imports[0].is_conditional is True
        assert imports[1].module == "json"
        assert imports[1].is_conditional is True


class TestImportAnalyzerLazy:
    """Tests for lazy (in-function) import handling."""

    def test_function_import(self) -> None:
        code = """
def load_heavy():
    import heavy_module
    return heavy_module.process()
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        assert imports[0].module == "heavy_module"
        assert imports[0].is_lazy is True

    def test_async_function_import(self) -> None:
        code = """
async def async_load():
    from aiohttp import ClientSession
    async with ClientSession() as session:
        pass
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        assert imports[0].is_lazy is True

    def test_method_import(self) -> None:
        code = """
class Loader:
    def load(self):
        import lazy_module
        return lazy_module
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        assert imports[0].is_lazy is True


class TestImportAnalyzerCombined:
    """Tests for combined scenarios."""

    def test_type_checking_in_class(self) -> None:
        code = """
from typing import TYPE_CHECKING

class Foo:
    if TYPE_CHECKING:
        from mypackage import Bar
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 2
        assert imports[1].is_type_checking is True

    def test_conditional_inside_function(self) -> None:
        code = """
def conditional_import():
    if should_import:
        import optional_module
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 1
        assert imports[0].is_lazy is True
        assert imports[0].is_conditional is True

    def test_complete_module(self) -> None:
        code = """
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypackage import TypeOnly

def lazy_load():
    import heavy
    return heavy

class MyClass:
    pass
"""
        tree = make_tree(code)
        analyzer = ImportAnalyzer()

        imports = analyzer.analyze(tree, Path("test.py"), "mypackage.module")

        assert len(imports) == 4
        # os - normal
        assert imports[0].module == "os"
        assert imports[0].is_type_checking is False
        assert imports[0].is_lazy is False

        # TYPE_CHECKING - normal
        assert imports[1].module == "typing"

        # TypeOnly - type checking
        assert imports[2].module == "mypackage"
        assert imports[2].is_type_checking is True

        # heavy - lazy
        assert imports[3].module == "heavy"
        assert imports[3].is_lazy is True
