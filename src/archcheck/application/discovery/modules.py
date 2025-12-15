"""Module discovery from directory structure."""

from __future__ import annotations

from pathlib import Path


def discover_modules(app_dir: Path, package_name: str) -> frozenset[str]:
    """Discover all module FQNs in app_dir.

    Recursively scans app_dir for .py files and converts paths to
    fully qualified module names.

    Args:
        app_dir: Application source directory to scan
        package_name: Root package name (e.g., "myapp")

    Returns:
        Frozenset of fully qualified module names

    Raises:
        ValueError: If app_dir is not a directory
        ValueError: If package_name is empty

    Example:
        >>> discover_modules(Path("src/myapp"), "myapp")
        frozenset({'myapp.domain.model', 'myapp.services.auth', ...})
    """
    if not app_dir.is_dir():
        raise ValueError(f"app_dir must be a directory: {app_dir}")

    if not package_name:
        raise ValueError("package_name must not be empty")

    modules: set[str] = set()

    for py_file in app_dir.rglob("*.py"):
        # Skip __pycache__
        if "__pycache__" in py_file.parts:
            continue

        # Convert path to module name
        relative = py_file.relative_to(app_dir)
        parts = list(relative.with_suffix("").parts)

        # Handle __init__.py
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]

        # Skip empty (root __init__.py)
        if not parts:
            modules.add(package_name)
            continue

        # Validate all parts are valid identifiers
        if not all(part.isidentifier() for part in parts):
            continue

        module_name = f"{package_name}.{'.'.join(parts)}"
        modules.add(module_name)

    return frozenset(modules)
