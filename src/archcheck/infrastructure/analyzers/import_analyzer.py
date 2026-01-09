"""Import analyzer: AST → Import domain objects.

Extracts all imports from a module AST.
Handles: import X, from X import Y, relative imports.
"""

from __future__ import annotations

import ast

from archcheck.domain.codebase import Import


def analyze_imports(tree: ast.Module) -> tuple[Import, ...]:
    """Extract imports from module AST.

    Handles:
        import typing             → Import("typing", None, None, False, 0)
        from typing import X      → Import("typing", "X", None, False, 0)
        from typing import X as Y → Import("typing", "X", "Y", False, 0)
        from . import foo         → Import("", "foo", None, True, 1)
        from ..sub import bar     → Import("sub", "bar", None, True, 2)

    Args:
        tree: Parsed AST module.

    Returns:
        Tuple of Import objects in source order.
    """
    imports: list[Import] = []

    for node in ast.iter_child_nodes(tree):
        match node:
            case ast.Import():
                imports.extend(_handle_import(node))
            case ast.ImportFrom():
                imports.extend(_handle_import_from(node))

    return tuple(imports)


def _handle_import(node: ast.Import) -> list[Import]:
    """Handle: import X, import X as Y, import X, Y."""
    return [
        Import(
            module=alias.name,
            name=None,
            alias=alias.asname,
            is_relative=False,
            level=0,
        )
        for alias in node.names
    ]


def _handle_import_from(node: ast.ImportFrom) -> list[Import]:
    """Handle: from X import Y, from . import Y, from ..X import Y."""
    module = node.module or ""
    level = node.level
    is_relative = level > 0

    return [
        Import(
            module=module,
            name=alias.name,
            alias=alias.asname,
            is_relative=is_relative,
            level=level,
        )
        for alias in node.names
    ]
