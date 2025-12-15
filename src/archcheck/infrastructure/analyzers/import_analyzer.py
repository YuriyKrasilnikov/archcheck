"""Import statement analyzer."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from archcheck.domain.model.import_ import Import
from archcheck.infrastructure.analyzers.base import make_location, resolve_relative_import
from archcheck.infrastructure.analyzers.context import AnalysisContext, ContextType

if TYPE_CHECKING:
    from pathlib import Path


class ImportAnalyzer:
    """Extracts imports from Python AST.

    Stateless analyzer - no state between analyze() calls.
    """

    def analyze(
        self,
        tree: ast.Module,
        path: Path,
        module_name: str,
    ) -> tuple[Import, ...]:
        """Extract all imports from module.

        Args:
            tree: Parsed AST module
            path: Source file path
            module_name: Fully qualified module name

        Returns:
            Tuple of Import objects
        """
        visitor = _ImportVisitor(path, module_name)
        visitor.visit(tree)
        return tuple(visitor.imports)


class _ImportVisitor(ast.NodeVisitor):
    """Collects imports with context tracking."""

    def __init__(self, path: Path, module_name: str) -> None:
        # FAIL-FIRST: validate required parameters
        if path is None:
            raise TypeError("path must not be None")
        if not module_name:
            raise ValueError("module_name must be non-empty string")

        self.path = path
        self.module_name = module_name
        self.imports: list[Import] = []
        self.context = AnalysisContext()

    def visit_Module(self, node: ast.Module) -> None:
        self.context.push(ContextType.MODULE)
        self.generic_visit(node)
        self.context.pop()

    def visit_Import(self, node: ast.Import) -> None:
        """Handle: import X, import X as Y."""
        for alias in node.names:
            self.imports.append(
                Import(
                    module=alias.name,
                    name=None,
                    alias=alias.asname,
                    location=make_location(node, self.path),
                    level=0,
                    is_type_checking=self.context.in_type_checking,
                    is_conditional=self.context.in_conditional,
                    is_lazy=self.context.in_function,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle: from X import Y, from . import Y."""
        # Resolve relative import to absolute
        resolved_module = resolve_relative_import(
            node.module,
            node.level,
            self.module_name,
        )

        for alias in node.names:
            self.imports.append(
                Import(
                    module=resolved_module,
                    name=alias.name,
                    alias=alias.asname,
                    location=make_location(node, self.path),
                    level=node.level,
                    is_type_checking=self.context.in_type_checking,
                    is_conditional=self.context.in_conditional,
                    is_lazy=self.context.in_function,
                )
            )

    def visit_If(self, node: ast.If) -> None:
        """Track TYPE_CHECKING and conditional blocks."""
        is_type_checking = self._is_type_checking_block(node)

        if is_type_checking:
            self.context.push(ContextType.TYPE_CHECKING)
        else:
            self.context.push(ContextType.CONDITIONAL)

        self.generic_visit(node)
        self.context.pop()

    def visit_Try(self, node: ast.Try) -> None:
        """Track try blocks as conditional."""
        self.context.push(ContextType.CONDITIONAL)
        self.generic_visit(node)
        self.context.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function scope for lazy imports."""
        self.context.push(ContextType.FUNCTION, node.name)
        self.generic_visit(node)
        self.context.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function scope for lazy imports."""
        self.context.push(ContextType.FUNCTION, node.name)
        self.generic_visit(node)
        self.context.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class scope."""
        self.context.push(ContextType.CLASS, node.name)
        self.generic_visit(node)
        self.context.pop()

    def _is_type_checking_block(self, node: ast.If) -> bool:
        """Check if if-statement is TYPE_CHECKING guard."""
        test = node.test

        # if TYPE_CHECKING:
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True

        # if typing.TYPE_CHECKING:
        if (
            isinstance(test, ast.Attribute)
            and test.attr == "TYPE_CHECKING"
            and isinstance(test.value, ast.Name)
            and test.value.id == "typing"
        ):
            return True

        return False
