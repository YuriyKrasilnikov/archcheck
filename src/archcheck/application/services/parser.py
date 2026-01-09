"""Parser service: parse Python source to Codebase and StaticCallGraph.

Orchestrates analyzers to build domain model from source files.
FAIL-FIRST: ParseError on syntax errors.
"""

import ast
from typing import TYPE_CHECKING

from archcheck.domain.codebase import Class, Codebase, Function, Module
from archcheck.domain.exceptions import ParseError
from archcheck.domain.static_graph import StaticCallEdge, StaticCallGraph, UnresolvedCall
from archcheck.infrastructure.analyzers import (
    analyze_class,
    analyze_function,
    analyze_imports,
    resolve_calls,
)

if TYPE_CHECKING:
    import pathlib

# Default directories to exclude from parsing
DEFAULT_EXCLUDES = frozenset(
    {
        "__pycache__",
        ".venv",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        ".tox",
        ".nox",
        "build",
        "dist",
        ".eggs",
    },
)


def parse_file(path: pathlib.Path, root_path: pathlib.Path) -> Module:
    """Parse single Python file to Module.

    Args:
        path: Path to .py file.
        root_path: Root directory for module name calculation.

    Returns:
        Module domain object.

    Raises:
        ParseError: Invalid Python syntax.
    """
    module_name = _compute_module_name(path, root_path)
    content = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError as e:
        raise ParseError(path=str(path), reason=str(e)) from e

    imports = analyze_imports(tree)
    functions = _extract_functions(tree, module_name)
    classes = _extract_classes(tree, module_name)
    docstring = ast.get_docstring(tree)

    return Module(
        name=module_name,
        path=path,
        imports=imports,
        classes=classes,
        functions=functions,
        docstring=docstring,
    )


def parse_directory(
    path: pathlib.Path,
    *,
    exclude: frozenset[str] = DEFAULT_EXCLUDES,
) -> tuple[Codebase, StaticCallGraph]:
    """Parse directory to Codebase and StaticCallGraph.

    Args:
        path: Root directory to parse.
        exclude: Directory names to skip.

    Returns:
        Tuple of (Codebase, StaticCallGraph).

    Raises:
        ParseError: Any file has invalid syntax.
    """
    root_path = path
    root_package = path.name

    # Find all .py files
    py_files = _find_python_files(path, exclude)

    # Parse each file
    modules: dict[str, Module] = {}
    for py_file in py_files:
        module = parse_file(py_file, root_path)
        modules[module.name] = module

    codebase = Codebase(
        root_path=root_path,
        root_package=root_package,
        modules=modules,
    )

    static_graph = build_static_graph(codebase)

    return codebase, static_graph


def build_static_graph(codebase: Codebase) -> StaticCallGraph:
    """Build StaticCallGraph from Codebase.

    Resolves all calls in all modules using call_resolver.

    Args:
        codebase: Parsed codebase.

    Returns:
        StaticCallGraph with resolved edges and unresolved calls.
    """
    all_edges: list[StaticCallEdge] = []
    all_unresolved: list[UnresolvedCall] = []

    for module in codebase.modules.values():
        edges, unresolved = resolve_calls(module, codebase)
        all_edges.extend(edges)
        all_unresolved.extend(unresolved)

    return StaticCallGraph(
        edges=tuple(all_edges),
        unresolved=tuple(all_unresolved),
    )


def _compute_module_name(path: pathlib.Path, root_path: pathlib.Path) -> str:
    """Compute Python module name from file path.

    Examples:
        /src/app/utils.py, /src → app.utils
        /src/app/__init__.py, /src → app
        /src/app/services/user.py, /src → app.services.user
    """
    relative = path.relative_to(root_path)

    # Remove .py suffix
    stem = relative.with_suffix("")

    # Convert path to module name
    parts = stem.parts

    # __init__.py → parent directory is module
    if parts[-1] == "__init__":
        parts = parts[:-1]

    return ".".join(parts)


def _find_python_files(root: pathlib.Path, exclude: frozenset[str]) -> list[pathlib.Path]:
    """Find all .py files in directory, excluding specified directories."""
    result: list[pathlib.Path] = []

    for item in root.iterdir():
        if item.is_dir():
            if item.name not in exclude:
                result.extend(_find_python_files(item, exclude))
        elif item.is_file() and item.suffix == ".py":
            result.append(item)

    return result


def _extract_functions(tree: ast.Module, module_name: str) -> tuple[Function, ...]:
    """Extract top-level functions from AST."""
    functions: list[Function] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func = analyze_function(node, module_name)
            functions.append(func)

    return tuple(functions)


def _extract_classes(tree: ast.Module, module_name: str) -> tuple[Class, ...]:
    """Extract classes from AST."""
    classes: list[Class] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            cls = analyze_class(node, module_name)
            classes.append(cls)

    return tuple(classes)
