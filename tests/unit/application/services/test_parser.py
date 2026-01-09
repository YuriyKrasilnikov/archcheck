"""Tests for parser service.

Tests:
- parse_file: single file parsing
- parse_directory: directory parsing
- build_static_graph: graph construction
- _compute_module_name: module name calculation
- Error handling: ParseError on syntax errors
"""

from typing import TYPE_CHECKING

import pytest

from archcheck.application.services.parser import (
    DEFAULT_EXCLUDES,
    build_static_graph,
    parse_directory,
    parse_file,
)
from archcheck.domain.codebase import Codebase
from archcheck.domain.exceptions import ParseError
from archcheck.domain.static_graph import StaticCallGraph

if TYPE_CHECKING:
    from pathlib import Path


class TestParseFile:
    """Tests for parse_file()."""

    def test_simple_module(self, tmp_path: Path) -> None:
        """Parse module with function."""
        code = "def foo(): pass"
        file = tmp_path / "test.py"
        file.write_text(code)

        module = parse_file(file, tmp_path)

        assert module.name == "test"
        assert module.path == file
        assert len(module.functions) == 1
        assert module.functions[0].name == "foo"

    def test_module_with_class(self, tmp_path: Path) -> None:
        """Parse module with class."""
        code = """
class Service:
    def process(self): pass
"""
        file = tmp_path / "service.py"
        file.write_text(code)

        module = parse_file(file, tmp_path)

        assert len(module.classes) == 1
        assert module.classes[0].name == "Service"
        assert len(module.classes[0].methods) == 1

    def test_module_with_imports(self, tmp_path: Path) -> None:
        """Parse module with imports."""
        code = """
import os
from typing import Optional
"""
        file = tmp_path / "imports.py"
        file.write_text(code)

        module = parse_file(file, tmp_path)

        assert len(module.imports) == 2

    def test_nested_module_name(self, tmp_path: Path) -> None:
        """Module name from nested path."""
        (tmp_path / "app" / "services").mkdir(parents=True)
        file = tmp_path / "app" / "services" / "user.py"
        file.write_text("pass")

        module = parse_file(file, tmp_path)

        assert module.name == "app.services.user"

    def test_init_module_name(self, tmp_path: Path) -> None:
        """__init__.py becomes package name."""
        (tmp_path / "app").mkdir()
        file = tmp_path / "app" / "__init__.py"
        file.write_text("pass")

        module = parse_file(file, tmp_path)

        assert module.name == "app"

    def test_syntax_error_raises_parse_error(self, tmp_path: Path) -> None:
        """Invalid Python raises ParseError."""
        code = "def broken("
        file = tmp_path / "broken.py"
        file.write_text(code)

        with pytest.raises(ParseError) as exc_info:
            parse_file(file, tmp_path)

        assert str(file) in exc_info.value.path

    def test_docstring_extracted(self, tmp_path: Path) -> None:
        """Module docstring extracted."""
        code = '"""This is the module docstring."""\n\ndef foo(): pass'
        file = tmp_path / "doc.py"
        file.write_text(code)

        module = parse_file(file, tmp_path)

        assert module.docstring == "This is the module docstring."


class TestParseDirectory:
    """Tests for parse_directory()."""

    def test_single_file(self, tmp_path: Path) -> None:
        """Parse directory with single file."""
        file = tmp_path / "main.py"
        file.write_text("def main(): pass")

        codebase, _graph = parse_directory(tmp_path)

        assert len(codebase.modules) == 1
        assert "main" in codebase.modules

    def test_multiple_files(self, tmp_path: Path) -> None:
        """Parse directory with multiple files."""
        (tmp_path / "a.py").write_text("def a(): pass")
        (tmp_path / "b.py").write_text("def b(): pass")

        codebase, _graph = parse_directory(tmp_path)

        assert len(codebase.modules) == 2

    def test_nested_structure(self, tmp_path: Path) -> None:
        """Parse nested directory structure."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "main.py").write_text("def main(): pass")

        codebase, _graph = parse_directory(tmp_path)

        assert "app" in codebase.modules
        assert "app.main" in codebase.modules

    def test_excludes_pycache(self, tmp_path: Path) -> None:
        """__pycache__ excluded by default."""
        (tmp_path / "main.py").write_text("pass")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.py").write_text("pass")

        codebase, _graph = parse_directory(tmp_path)

        assert len(codebase.modules) == 1
        assert all("__pycache__" not in name for name in codebase.modules)

    def test_excludes_venv(self, tmp_path: Path) -> None:
        """.venv excluded by default."""
        (tmp_path / "main.py").write_text("pass")
        (tmp_path / ".venv" / "lib").mkdir(parents=True)
        (tmp_path / ".venv" / "lib" / "site.py").write_text("pass")

        codebase, _graph = parse_directory(tmp_path)

        assert len(codebase.modules) == 1

    def test_custom_exclude(self, tmp_path: Path) -> None:
        """Custom exclude patterns."""
        (tmp_path / "main.py").write_text("pass")
        (tmp_path / "vendor").mkdir()
        (tmp_path / "vendor" / "lib.py").write_text("pass")

        codebase, _graph = parse_directory(tmp_path, exclude=frozenset({"vendor"}))

        assert len(codebase.modules) == 1
        assert "main" in codebase.modules

    def test_returns_static_graph(self, tmp_path: Path) -> None:
        """Returns StaticCallGraph with codebase."""
        code = """
def caller():
    callee()

def callee():
    pass
"""
        (tmp_path / "main.py").write_text(code)

        _codebase, graph = parse_directory(tmp_path)

        assert isinstance(graph, StaticCallGraph)
        # caller → callee should be resolved
        assert any(e.callee_fqn == "main.callee" for e in graph.edges)


class TestBuildStaticGraph:
    """Tests for build_static_graph()."""

    def test_resolves_internal_calls(self, tmp_path: Path) -> None:
        """Resolves calls between modules."""
        (tmp_path / "caller.py").write_text("from callee import foo\ndef bar(): foo()")
        (tmp_path / "callee.py").write_text("def foo(): pass")

        codebase, _ = parse_directory(tmp_path)
        graph = build_static_graph(codebase)

        edge = next((e for e in graph.edges if e.caller_fqn == "caller.bar"), None)
        assert edge is not None
        assert edge.callee_fqn == "callee.foo"

    def test_tracks_unresolved(self, tmp_path: Path) -> None:
        """Tracks unresolved calls."""
        (tmp_path / "main.py").write_text("def foo(): unknown()")

        codebase, _ = parse_directory(tmp_path)
        graph = build_static_graph(codebase)

        assert any(u.callee_name == "unknown" for u in graph.unresolved)

    def test_empty_codebase(self) -> None:
        """Empty codebase returns empty graph."""
        codebase = Codebase.empty()
        graph = build_static_graph(codebase)

        assert graph.edges == ()
        assert graph.unresolved == ()


class TestDefaultExcludes:
    """Tests for DEFAULT_EXCLUDES constant."""

    def test_contains_pycache(self) -> None:
        """Contains __pycache__."""
        assert "__pycache__" in DEFAULT_EXCLUDES

    def test_contains_venv(self) -> None:
        """Contains .venv."""
        assert ".venv" in DEFAULT_EXCLUDES

    def test_contains_git(self) -> None:
        """Contains .git."""
        assert ".git" in DEFAULT_EXCLUDES

    def test_is_frozenset(self) -> None:
        """Is immutable frozenset."""
        assert isinstance(DEFAULT_EXCLUDES, frozenset)
