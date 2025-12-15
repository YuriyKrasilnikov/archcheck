"""AST-based source parser adapter.

Implements SourceParserPort using Python AST.
Builds Codebase with all graphs (import, inheritance, call).
"""

from __future__ import annotations

import ast
from pathlib import Path

from archcheck.domain.exceptions.parsing import ParsingError
from archcheck.domain.model.call_graph import CallGraph
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.import_graph import ImportGraph
from archcheck.domain.model.inheritance_graph import InheritanceGraph
from archcheck.domain.model.module import Module
from archcheck.domain.model.symbol_table import SymbolTable
from archcheck.domain.ports.source_parser import SourceParserPort
from archcheck.infrastructure.analyzers.base import compute_module_name
from archcheck.infrastructure.analyzers.class_analyzer import ClassAnalyzer
from archcheck.infrastructure.analyzers.class_resolver import ClassResolver
from archcheck.infrastructure.analyzers.function_analyzer import FunctionAnalyzer
from archcheck.infrastructure.analyzers.import_analyzer import ImportAnalyzer


class ASTSourceParser(SourceParserPort):
    """Parser using Python AST to extract code structure.

    Stateless between parse_file() calls.
    Builds graphs after all modules parsed in parse_directory().

    FAIL-FIRST: raises ParsingError on any parsing issue.
    """

    def __init__(self, root_path: Path) -> None:
        """Initialize parser with root path.

        Args:
            root_path: Root path for computing module names

        Raises:
            TypeError: If root_path is None
        """
        if root_path is None:
            raise TypeError("root_path must not be None")

        self._root_path = root_path
        self._import_analyzer = ImportAnalyzer()
        self._function_analyzer = FunctionAnalyzer()
        self._class_analyzer = ClassAnalyzer()
        self._class_resolver = ClassResolver()

    def parse_file(self, path: Path) -> Module:
        """Parse single Python file.

        FAIL-FIRST: raises ParsingError on file errors, syntax errors.

        Args:
            path: Path to .py file

        Returns:
            Parsed Module

        Raises:
            ParsingError: If file cannot be read or parsed
        """
        # Read file - FAIL-FIRST on file errors
        try:
            source = path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise ParsingError(path, "file not found") from e
        except PermissionError as e:
            raise ParsingError(path, "permission denied") from e
        except UnicodeDecodeError as e:
            raise ParsingError(path, f"encoding error: {e}") from e

        # Parse AST - FAIL-FIRST on syntax errors
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            raise ParsingError(path, f"syntax error: {e}") from e

        module_name = compute_module_name(path, self._root_path)

        # Extract imports
        imports = self._import_analyzer.analyze(tree, path, module_name)

        # Build symbol table for name resolution
        symbol_table = SymbolTable()
        for imp in imports:
            symbol_table.add_import(imp)

        # Collect known class names in this module (for CONSTRUCTOR detection)
        known_classes = frozenset(node.name for node in tree.body if isinstance(node, ast.ClassDef))

        # Extract classes (with symbol_table for method body resolution)
        classes = tuple(
            self._class_analyzer.analyze(node, path, module_name, symbol_table, known_classes)
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        )

        # Resolve classes for interface/implementation detection
        resolved_classes = self._class_resolver.resolve(classes, symbol_table)

        # Extract module-level functions (with symbol_table for body resolution)
        functions = tuple(
            self._function_analyzer.analyze(
                node, path, module_name, None, symbol_table, known_classes
            )
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        )

        # Extract constants
        constants = _extract_constants(tree)

        # Extract docstring
        docstring = ast.get_docstring(tree, clean=True)

        return Module(
            name=module_name,
            path=path,
            imports=imports,
            classes=classes,
            functions=functions,
            constants=constants,
            docstring=docstring,
            resolved_classes=resolved_classes,
        )

    def parse_directory(self, path: Path, package_name: str) -> Codebase:
        """Parse directory recursively with graph building.

        Parses all .py files, skipping __pycache__.
        Builds import, inheritance, and call graphs after all modules parsed.

        Args:
            path: Root directory path
            package_name: Root package name

        Returns:
            Codebase with all modules and graphs

        Raises:
            ParsingError: If any file cannot be parsed
        """
        codebase = Codebase(root_path=path, root_package=package_name)

        # Parse all .py files
        for py_file in path.rglob("*.py"):
            # Skip __pycache__ directories
            if "__pycache__" in py_file.parts:
                continue

            module = self.parse_file(py_file)
            codebase.add_module(module)

        # Build graphs after all modules parsed
        codebase.set_import_graph(ImportGraph.from_modules(codebase.modules))
        codebase.set_inheritance_graph(InheritanceGraph.from_modules(codebase.modules))
        codebase.set_call_graph(CallGraph.from_modules(codebase.modules))

        return codebase


def _extract_constants(tree: ast.Module) -> tuple[str, ...]:
    """Extract UPPER_CASE constant names from module.

    Constants are identified by UPPER_CASE naming convention.
    Supports both regular and annotated assignments.

    Args:
        tree: Parsed AST module

    Returns:
        Tuple of constant names
    """
    constants: list[str] = []

    for node in tree.body:
        match node:
            case ast.Assign(targets=targets):
                for target in targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        constants.append(target.id)

            case ast.AnnAssign(target=ast.Name(id=name)) if name.isupper():
                constants.append(name)

    return tuple(constants)
