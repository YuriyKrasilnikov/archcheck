"""Tests for import_analyzer.

Tests:
- import X
- import X as Y
- from X import Y
- from X import Y as Z
- from . import foo
- from .. import bar
- from .sub import baz
- Multiple imports in one statement
- Multiple import statements
"""

import ast

from archcheck.domain.codebase import Import
from archcheck.infrastructure.analyzers.import_analyzer import analyze_imports


class TestAnalyzeImports:
    """Tests for analyze_imports()."""

    def test_import_module(self) -> None:
        """Import typing."""
        code = "import typing"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0] == Import(
            module="typing",
            name=None,
            alias=None,
            is_relative=False,
            level=0,
        )

    def test_import_module_alias(self) -> None:
        """Import typing as t."""
        code = "import typing as t"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0].module == "typing"
        assert imports[0].alias == "t"

    def test_import_multiple_modules(self) -> None:
        """Import os, sys."""
        code = "import os, sys"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 2
        assert imports[0].module == "os"
        assert imports[1].module == "sys"

    def test_from_import(self) -> None:
        """From typing import Optional."""
        code = "from typing import Optional"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0] == Import(
            module="typing",
            name="Optional",
            alias=None,
            is_relative=False,
            level=0,
        )

    def test_from_import_alias(self) -> None:
        """From typing import Optional as Opt."""
        code = "from typing import Optional as Opt"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0].name == "Optional"
        assert imports[0].alias == "Opt"

    def test_from_import_multiple(self) -> None:
        """From typing import Optional, List."""
        code = "from typing import Optional, List"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 2
        assert imports[0].name == "Optional"
        assert imports[1].name == "List"

    def test_relative_import_current(self) -> None:
        """From . import foo."""
        code = "from . import foo"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0] == Import(
            module="",
            name="foo",
            alias=None,
            is_relative=True,
            level=1,
        )

    def test_relative_import_parent(self) -> None:
        """From .. import bar."""
        code = "from .. import bar"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0].level == 2
        assert imports[0].is_relative is True

    def test_relative_import_submodule(self) -> None:
        """From .sub import baz."""
        code = "from .sub import baz"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0].module == "sub"
        assert imports[0].name == "baz"
        assert imports[0].level == 1

    def test_relative_import_parent_submodule(self) -> None:
        """From ..sub.module import func."""
        code = "from ..sub.module import func"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0].module == "sub.module"
        assert imports[0].name == "func"
        assert imports[0].level == 2

    def test_multiple_statements(self) -> None:
        """Multiple import statements."""
        code = """
import os
from typing import Optional
from . import utils
"""
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 3
        assert imports[0].module == "os"
        assert imports[1].module == "typing"
        assert imports[2].is_relative is True

    def test_empty_module(self) -> None:
        """Module with no imports."""
        code = "x = 1"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 0

    def test_from_import_star(self) -> None:
        """From typing import *."""
        code = "from typing import *"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0].name == "*"

    def test_dotted_import(self) -> None:
        """Import os.path."""
        code = "import os.path"
        tree = ast.parse(code)

        imports = analyze_imports(tree)

        assert len(imports) == 1
        assert imports[0].module == "os.path"
