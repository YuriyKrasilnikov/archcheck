"""Decorator analyzer."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from archcheck.domain.model.decorator import Decorator
from archcheck.infrastructure.analyzers.base import make_location, unparse_node

if TYPE_CHECKING:
    from pathlib import Path


class DecoratorAnalyzer:
    """Extracts decorators from Python AST.

    Stateless analyzer - no state between analyze() calls.
    """

    def analyze(
        self,
        decorator_list: list[ast.expr],
        path: Path,
    ) -> tuple[Decorator, ...]:
        """Extract decorators from decorator list.

        Args:
            decorator_list: List of decorator expressions from AST
            path: Source file path

        Returns:
            Tuple of Decorator objects

        Raises:
            TypeError: If path is None (FAIL-FIRST)
        """
        # FAIL-FIRST: validate required parameters
        if path is None:
            raise TypeError("path must not be None")

        decorators: list[Decorator] = []

        for dec_node in decorator_list:
            decorators.append(self._analyze_decorator(dec_node, path))

        return tuple(decorators)

    def _analyze_decorator(self, node: ast.expr, path: Path) -> Decorator:
        """Analyze single decorator expression.

        Args:
            node: Decorator AST expression
            path: Source file path

        Returns:
            Decorator object
        """
        name: str
        arguments: tuple[str, ...]

        if isinstance(node, ast.Name):
            # @decorator
            name = node.id
            arguments = ()
        elif isinstance(node, ast.Attribute):
            # @module.decorator
            name = unparse_node(node)
            arguments = ()
        elif isinstance(node, ast.Call):
            # @decorator(...) or @module.decorator(...)
            name = self._get_call_name(node.func)
            arguments = self._get_call_arguments(node)
        else:
            # Fallback for complex expressions
            name = unparse_node(node)
            arguments = ()

        return Decorator(
            name=name,
            arguments=arguments,
            location=make_location(node, path),
        )

    def _get_call_name(self, func: ast.expr) -> str:
        """Get name from call function expression.

        Args:
            func: Function part of Call node

        Returns:
            Decorator name
        """
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return unparse_node(func)
        return unparse_node(func)

    def _get_call_arguments(self, node: ast.Call) -> tuple[str, ...]:
        """Extract arguments from decorator call.

        Args:
            node: Call AST node

        Returns:
            Tuple of argument strings
        """
        args: list[str] = []

        # Positional arguments
        for arg in node.args:
            args.append(unparse_node(arg))

        # Keyword arguments
        for kw in node.keywords:
            if kw.arg is not None:
                args.append(f"{kw.arg}={unparse_node(kw.value)}")
            else:
                # **kwargs unpacking
                args.append(f"**{unparse_node(kw.value)}")

        return tuple(args)
