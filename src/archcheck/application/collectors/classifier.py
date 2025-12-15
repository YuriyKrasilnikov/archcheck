"""Callee classification for runtime call graph analysis.

Classifies callees by their file location:
- APP: Application code under base_dir (not tests/)
- TEST: Test code under tests/ directory
- LIB: Known external library under site-packages
- OTHER: Unknown/stdlib/other code
"""

from __future__ import annotations

import sysconfig
from pathlib import Path

from archcheck.domain.model.callee_info import CalleeInfo
from archcheck.domain.model.callee_kind import CalleeKind

# Discover site-packages paths from sysconfig (not hardcoded)
_SITE_PACKAGES_PATHS: frozenset[Path] = frozenset(
    Path(p).resolve()
    for p in (
        sysconfig.get_path("purelib"),
        sysconfig.get_path("platlib"),
    )
    if p is not None
)


def classify_callee(
    filename: str,
    base_dir: Path,
    known_libs: frozenset[str],
) -> CalleeInfo:
    """Classify callee by filename.

    Algorithm:
    1. Under base_dir? → APP or TEST (by first path component)
    2. Under site-packages? → LIB if in known_libs, else OTHER
    3. Check path parts for known lib names (editable installs)
    4. Otherwise → OTHER (stdlib, unknown)

    Args:
        filename: Absolute path to source file (from code.co_filename)
        base_dir: Application root directory
        known_libs: Normalized library names from requirements

    Returns:
        CalleeInfo with classification result
    """
    path = Path(filename).resolve()
    base_dir_resolved = base_dir.resolve()

    # 1. Check if under base_dir (APP/TEST)
    app_result = _classify_app_or_test(path, base_dir_resolved)
    if app_result is not None:
        return app_result

    # 2. Check if under site-packages (LIB)
    lib_result = _classify_site_packages(path, known_libs)
    if lib_result is not None:
        return lib_result

    # 3. Check path parts for known lib names (editable installs)
    editable_result = _classify_editable_install(path, known_libs)
    if editable_result is not None:
        return editable_result

    # 4. Default: OTHER (stdlib, unknown code)
    return CalleeInfo(kind=CalleeKind.OTHER)


def _classify_app_or_test(path: Path, base_dir: Path) -> CalleeInfo | None:
    """Classify as APP or TEST if under base_dir."""
    try:
        relative = path.relative_to(base_dir)
    except ValueError:
        return None  # Not under base_dir

    parts = relative.parts
    if not parts:
        return None

    # tests/ directory → TEST
    if parts[0] == "tests":
        module = _path_to_module(relative)
        return CalleeInfo(kind=CalleeKind.TEST, module=module)

    # Any other directory under base_dir → APP
    module = _path_to_module(relative)
    return CalleeInfo(kind=CalleeKind.APP, module=module)


def _classify_site_packages(
    path: Path,
    known_libs: frozenset[str],
) -> CalleeInfo | None:
    """Classify as LIB if under site-packages and in known_libs."""
    for site_path in _SITE_PACKAGES_PATHS:
        try:
            relative = path.relative_to(site_path)
        except ValueError:
            continue

        parts = relative.parts
        if not parts:
            continue

        # First part is package name
        package_name = _normalize_lib_name(parts[0])
        if package_name in known_libs:
            return CalleeInfo(kind=CalleeKind.LIB, lib_name=package_name)

    return None


def _classify_editable_install(
    path: Path,
    known_libs: frozenset[str],
) -> CalleeInfo | None:
    """Classify as LIB if path contains known lib name (editable installs)."""
    path_parts_normalized = frozenset(_normalize_lib_name(p) for p in path.parts)

    for lib in known_libs:
        if lib in path_parts_normalized:
            return CalleeInfo(kind=CalleeKind.LIB, lib_name=lib)

    return None


def _path_to_module(relative: Path) -> str:
    """Convert relative path to module FQN."""
    parts = list(relative.with_suffix("").parts)

    # Handle __init__.py
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]

    if not parts:
        return "__init__"

    return ".".join(parts)


def _normalize_lib_name(name: str) -> str:
    """Normalize library name for consistent matching.

    - Lowercase
    - Replace - and . with _
    """
    return name.lower().replace("-", "_").replace(".", "_")
