"""Module predicates."""

import re
from fnmatch import fnmatch
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.module import Module

from archcheck.domain.predicates.base import ModulePredicate


def is_in_package(pattern: str) -> ModulePredicate:
    """Create predicate: module is in package matching pattern.

    Args:
        pattern: Glob pattern for package name

    Returns:
        Predicate function
    """

    def predicate(module: Module) -> bool:
        return fnmatch(module.name, pattern) or fnmatch(module.package, pattern)

    return predicate


def has_name_matching(regex: str) -> ModulePredicate:
    """Create predicate: module name matches regex.

    Args:
        regex: Regular expression pattern

    Returns:
        Predicate function

    Raises:
        ValueError: If regex is invalid
    """
    try:
        compiled = re.compile(regex)
    except re.error as e:
        raise ValueError(f"Invalid regex '{regex}': {e}") from e

    def predicate(module: Module) -> bool:
        return compiled.search(module.name) is not None

    return predicate


def has_import(module_pattern: str) -> ModulePredicate:
    """Create predicate: module imports matching pattern.

    Args:
        module_pattern: Glob pattern for imported module

    Returns:
        Predicate function
    """

    def predicate(module: Module) -> bool:
        return any(fnmatch(imp.module, module_pattern) for imp in module.imports)

    return predicate
