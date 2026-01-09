"""Class analyzer: AST → Class domain objects.

Extracts class definition from AST.
Detects: Protocol, dataclass, ABC.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from archcheck.domain.codebase import Class
from archcheck.domain.events import Location
from archcheck.infrastructure.analyzers.function_analyzer import analyze_function

if TYPE_CHECKING:
    from archcheck.domain.codebase import Function


def analyze_class(node: ast.ClassDef, module_name: str) -> Class:
    """Extract Class from AST node.

    Args:
        node: AST ClassDef node.
        module_name: Fully qualified module name.

    Returns:
        Class domain object.
    """
    name = node.name
    qualified_name = f"{module_name}.{name}"

    return Class(
        name=name,
        qualified_name=qualified_name,
        bases=_extract_bases(node),
        methods=_extract_methods(node, module_name, name),
        location=Location(file=None, line=node.lineno, func=None),
        is_protocol=_is_protocol(node),
        is_dataclass=_is_dataclass(node),
    )


def _extract_bases(node: ast.ClassDef) -> tuple[str, ...]:
    """Extract base class names."""
    return tuple(ast.unparse(base) for base in node.bases)


def _extract_methods(
    node: ast.ClassDef,
    module_name: str,
    class_name: str,
) -> tuple[Function, ...]:
    """Extract methods from class body."""
    methods: list[Function] = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            method = analyze_function(item, module_name, class_name=class_name)
            methods.append(method)
    return tuple(methods)


def _is_protocol(node: ast.ClassDef) -> bool:
    """Check if class is a Protocol.

    Protocol detection:
    1. Base class named "Protocol"
    2. Base class is typing.Protocol or typing_extensions.Protocol
    """
    for base in node.bases:
        match base:
            case ast.Name(id="Protocol"):
                return True
            case ast.Attribute(attr="Protocol"):
                return True
    return False


def _is_dataclass(node: ast.ClassDef) -> bool:
    """Check if class has @dataclass decorator.

    Handles:
    - @dataclass
    - @dataclass()
    - @dataclass(frozen=True)
    - @dataclasses.dataclass
    """
    for dec in node.decorator_list:
        match dec:
            case ast.Name(id="dataclass"):
                return True
            case ast.Call(func=ast.Name(id="dataclass")):
                return True
            case ast.Attribute(attr="dataclass"):
                return True
            case ast.Call(func=ast.Attribute(attr="dataclass")):
                return True
    return False
