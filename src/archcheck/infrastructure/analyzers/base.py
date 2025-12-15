"""Base utilities for AST analyzers."""

from __future__ import annotations

import ast
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

from archcheck.domain.model.enums import Visibility

if TYPE_CHECKING:
    from pathlib import Path

    from archcheck.domain.model.location import Location


def make_location(node: ast.stmt | ast.expr, path: Path) -> Location:
    """Create Location from AST node.

    Args:
        node: AST node with position info (statement or expression)
        path: Source file path

    Returns:
        Location pointing to node

    Raises:
        ASTError: If node has no line info (FAIL-FIRST)
    """
    from archcheck.domain.exceptions.parsing import ASTError
    from archcheck.domain.model.location import Location

    # FAIL-FIRST: node must have line info
    lineno = getattr(node, "lineno", None)
    if lineno is None:
        raise ASTError(
            path,
            Location(file=path, line=1, column=0),
            "node has no line info",
        )

    return Location(
        file=path,
        line=lineno,
        column=node.col_offset,
        end_line=node.end_lineno,
        end_column=node.end_col_offset,
    )


def get_visibility(name: str) -> Visibility:
    """Determine visibility from Python naming convention.

    Args:
        name: Identifier name

    Returns:
        Visibility based on underscore prefix

    Rules:
        __name__ (dunder) → PUBLIC (special methods)
        __name (not __name__) → PRIVATE (mangled)
        _name → PROTECTED
        name → PUBLIC
    """
    # Dunder methods (__init__, __str__, etc.) are PUBLIC
    if name.startswith("__") and name.endswith("__"):
        return Visibility.PUBLIC
    # Name-mangled private attributes
    if name.startswith("__"):
        return Visibility.PRIVATE
    # Protected by convention
    if name.startswith("_"):
        return Visibility.PROTECTED
    return Visibility.PUBLIC


def compute_module_name(file_path: Path, root_path: Path) -> str:
    """Compute fully qualified module name from file path.

    Args:
        file_path: Path to .py file
        root_path: Project root path

    Returns:
        Fully qualified module name

    Raises:
        ParsingError: If path is invalid (FAIL-FIRST)
    """
    from archcheck.domain.exceptions.parsing import ParsingError

    try:
        relative = file_path.relative_to(root_path)
    except ValueError as e:
        raise ParsingError(file_path, f"not under {root_path}") from e

    parts = list(relative.with_suffix("").parts)

    if parts and parts[-1] == "__init__":
        parts = parts[:-1]

    for part in parts:
        if not part.isidentifier():
            raise ParsingError(file_path, f"'{part}' is not valid Python identifier")

    if not parts:
        raise ParsingError(file_path, "cannot determine module name (empty)")

    return ".".join(parts)


def resolve_relative_import(
    node_module: str | None,
    node_level: int,
    current_module: str,
) -> str:
    """Resolve relative import to absolute module path.

    Args:
        node_module: Module part of import (after dots)
        node_level: Number of dots (0=absolute, 1=., 2=..)
        current_module: Current module's fully qualified name

    Returns:
        Absolute module path

    Raises:
        ValueError: If relative import escapes package (FAIL-FIRST)
    """
    if node_level == 0:
        if node_module is None:
            raise ValueError("absolute import must have module")
        return node_module

    parts = current_module.split(".")

    if node_level > len(parts):
        raise ValueError(
            f"relative import level {node_level} exceeds package depth of module '{current_module}'"
        )

    base_parts = parts[:-node_level] if node_level > 0 else parts

    if node_module:
        return ".".join([*base_parts, node_module])

    if not base_parts:
        raise ValueError(f"relative import results in empty module from '{current_module}'")

    return ".".join(base_parts)


def unparse_node(node: ast.expr) -> str:
    """Convert AST expression to source string.

    Args:
        node: AST expression node

    Returns:
        Source code representation
    """
    return ast.unparse(node)


# =============================================================================
# SHALLOW WALK - Functional approach to single-scope AST traversal
# =============================================================================


def shallow_walk(body: Iterable[ast.stmt]) -> Iterator[ast.AST]:
    """Walk AST nodes in body without entering nested scopes.

    Yields all nodes in the body, but stops at scope boundaries:
    - FunctionDef, AsyncFunctionDef (yields node, not children)
    - ClassDef (yields node, not children)
    - Lambda (yields node, not children)

    This is the functional alternative to ast.NodeVisitor for single-scope analysis.

    Args:
        body: List of statements to traverse

    Yields:
        AST nodes in depth-first order, excluding nested scope internals

    Example:
        for node in shallow_walk(func.body):
            match node:
                case ast.Yield():
                    print("Found yield!")
                case ast.FunctionDef(name=name):
                    print(f"Skipping nested function: {name}")
    """
    stack: list[ast.AST] = list(reversed(list(body)))

    while stack:
        node = stack.pop()
        yield node

        match node:
            # Scope boundaries - yield node but don't traverse children
            case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef() | ast.Lambda():
                pass
            case _:
                # Add children in reverse order to maintain depth-first order
                stack.extend(reversed(list(ast.iter_child_nodes(node))))


# =============================================================================
# ALGORITHMS - Pure functions using pattern matching (Python 3.10+)
# =============================================================================


def is_generator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if function is generator.

    Uses shallow_walk to properly skip nested functions.
    Nested functions with yield don't make parent a generator.

    Args:
        node: Function node to check

    Returns:
        True if function contains yield/yield from at its own level
    """
    for child in shallow_walk(node.body):
        match child:
            case ast.Yield() | ast.YieldFrom():
                return True
    return False


def extract_init_attributes(init_node: ast.FunctionDef) -> frozenset[str]:
    """Extract self.x attributes assigned in __init__.

    Uses shallow_walk and pattern matching.
    Supports: regular assignment, annotated assignment, augmented assignment, walrus operator.

    Args:
        init_node: __init__ method AST node

    Returns:
        Set of attribute names assigned to self
    """
    attributes: set[str] = set()

    for node in shallow_walk(init_node.body):
        match node:
            case ast.Assign(targets=targets):
                for target in targets:
                    if attr := _extract_self_attr(target):
                        attributes.add(attr)

            case ast.AnnAssign(target=target, value=value) if value is not None:
                if attr := _extract_self_attr(target):
                    attributes.add(attr)

            case ast.AugAssign(target=target):
                if attr := _extract_self_attr(target):
                    attributes.add(attr)

            case ast.NamedExpr(target=target):
                if attr := _extract_self_attr(target):
                    attributes.add(attr)

    return frozenset(attributes)


def _extract_self_attr(node: ast.expr) -> str | None:
    """Extract attribute name if node is self.x pattern.

    Args:
        node: Expression node to check

    Returns:
        Attribute name if pattern matches, None otherwise
    """
    match node:
        case ast.Attribute(value=ast.Name(id="self"), attr=attr):
            return attr
    return None


def extract_base_names(class_node: ast.ClassDef) -> tuple[str, ...]:
    """Extract base class names from class definition.

    Args:
        class_node: Class AST node

    Returns:
        Tuple of base class names as they appear in code
    """
    bases: list[str] = []
    for base in class_node.bases:
        bases.append(ast.unparse(base))
    return tuple(bases)


def has_decorator(
    decorators: list[ast.expr],
    name: str,
) -> bool:
    """Check if decorator list contains decorator with given name.

    Args:
        decorators: List of decorator expressions
        name: Decorator name to find

    Returns:
        True if decorator found
    """
    for dec in decorators:
        if isinstance(dec, ast.Name) and dec.id == name:
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == name:
            return True
        if isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name) and dec.func.id == name:
                return True
            if isinstance(dec.func, ast.Attribute) and dec.func.attr == name:
                return True
    return False


def get_docstring(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Module,
) -> str | None:
    """Extract docstring from AST node.

    Args:
        node: Function, class or module node

    Returns:
        Docstring or None
    """
    return ast.get_docstring(node, clean=True)
