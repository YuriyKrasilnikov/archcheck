"""Layer discovery from directory structure."""

from __future__ import annotations

from pathlib import Path


def discover_layers(app_dir: Path) -> frozenset[str]:
    """Discover layer names from directory structure.

    Scans app_dir for subdirectories that are valid Python identifiers.
    Directories starting with underscore are excluded.

    Args:
        app_dir: Application source directory to scan

    Returns:
        Frozenset of layer names (directory names)

    Raises:
        ValueError: If app_dir is not a directory

    Example:
        >>> discover_layers(Path("src/myapp"))
        frozenset({'domain', 'application', 'infrastructure', 'presentation'})
    """
    if not app_dir.is_dir():
        raise ValueError(f"app_dir must be a directory: {app_dir}")

    return frozenset(
        d.name
        for d in app_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and d.name.isidentifier()
    )
