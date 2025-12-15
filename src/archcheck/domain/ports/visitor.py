"""Visitor protocol for AST visitors.

Users extend archcheck by implementing this Protocol.
"""

from __future__ import annotations

import ast
from collections.abc import Sequence
from typing import Protocol, TypedDict


class ViolationDict(TypedDict, total=False):
    """Violation dictionary from visitors.

    Visitors return dicts instead of Violation objects
    to avoid coupling to domain model details.

    Required keys:
        file: File path as string
        line: Line number (1-based)
        message: Human-readable message

    Optional keys:
        column: Column number (0-based)
        rule_name: Name of the rule that was violated
        suggestion: Fix suggestion
    """

    file: str
    line: int
    message: str
    column: int
    rule_name: str
    suggestion: str


class VisitorProtocol(Protocol):
    """Contract for AST visitors.

    Users implement this Protocol to add custom AST-based checks.
    Visitors are stateless between files but accumulate violations.

    Example:
        class PrintDetector:
            def __init__(self) -> None:
                self._violations: list[ViolationDict] = []

            def visit(self, tree: ast.AST, file_path: str) -> None:
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id == "print":
                            self._violations.append({
                                "file": file_path,
                                "line": node.lineno,
                                "message": "print() not allowed in production code",
                            })

            @property
            def violations(self) -> Sequence[ViolationDict]:
                return self._violations
    """

    def visit(self, tree: ast.AST, file_path: str) -> None:
        """Visit AST tree and collect violations.

        Args:
            tree: Parsed AST tree
            file_path: Path to source file (for error messages)
        """
        ...

    @property
    def violations(self) -> Sequence[ViolationDict]:
        """Get collected violations.

        Returns:
            Sequence of violation dicts with file, line, message keys.
        """
        ...
