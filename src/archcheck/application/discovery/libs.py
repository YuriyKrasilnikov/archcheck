"""Known libraries discovery from requirements files."""

from __future__ import annotations

import re
from pathlib import Path

# Package name regex: starts with letter/digit, then alphanumeric, -, ., _
_PACKAGE_NAME_PATTERN = re.compile(r"^([a-zA-Z0-9][\w.-]*)")


def load_known_libs(requirements_path: Path) -> frozenset[str]:
    """Parse requirements file(s) to get known library names.

    Supports:
    - Single requirements.txt file
    - Directory containing .txt files (requirements/*.txt)

    Package names are normalized: lowercase, - and . replaced with _.

    Args:
        requirements_path: Path to requirements file or directory

    Returns:
        Frozenset of normalized library names

    Raises:
        FileNotFoundError: If path does not exist
        ValueError: If directory contains no .txt files

    Example:
        >>> load_known_libs(Path("requirements/base.txt"))
        frozenset({'aiohttp', 'sqlalchemy', 'pydantic'})
    """
    if not requirements_path.exists():
        raise FileNotFoundError(f"requirements path not found: {requirements_path}")

    if requirements_path.is_file():
        return _parse_requirements_file(requirements_path)

    if requirements_path.is_dir():
        return _parse_requirements_dir(requirements_path)

    raise ValueError(f"requirements_path must be file or directory: {requirements_path}")


def _parse_requirements_dir(requirements_dir: Path) -> frozenset[str]:
    """Parse all .txt files in requirements directory."""
    txt_files = list(requirements_dir.glob("*.txt"))

    if not txt_files:
        raise ValueError(f"no .txt files found in {requirements_dir}")

    libs: set[str] = set()
    for txt_file in txt_files:
        libs.update(_parse_requirements_file(txt_file))

    return frozenset(libs)


def _parse_requirements_file(file_path: Path) -> frozenset[str]:
    """Parse single requirements file."""
    libs: set[str] = set()

    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        # Skip empty, comments, options (-r, -e, etc.)
        if not line or line.startswith("#") or line.startswith("-"):
            continue

        # Extract package name (before ==, >=, <, [, etc.)
        match = _PACKAGE_NAME_PATTERN.match(line)
        if match:
            name = _normalize_lib_name(match.group(1))
            libs.add(name)

    return frozenset(libs)


def _normalize_lib_name(name: str) -> str:
    """Normalize library name for consistent matching.

    - Lowercase
    - Replace - and . with _

    This matches Python's import name normalization.
    """
    return name.lower().replace("-", "_").replace(".", "_")
