"""Extract module imports from Codebase."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from archcheck.domain.model.codebase import Codebase


def build_module_imports(codebase: Codebase) -> Mapping[str, frozenset[str]]:
    """Extract imports per module from Codebase.

    Returns mapping: module_fqn → set of imported module FQNs.
    Used by EdgeClassifier to determine if caller imports callee.

    Args:
        codebase: Parsed codebase with modules

    Returns:
        Immutable mapping from module FQN to set of imported module FQNs

    Raises:
        TypeError: If codebase is None (FAIL-FIRST)

    Complexity: O(M * I) where M=modules, I=avg imports per module
    """
    if codebase is None:
        raise TypeError("codebase must not be None")

    result: dict[str, frozenset[str]] = {}

    for module_name, module in codebase.modules.items():
        imported_modules: set[str] = set()

        for imp in module.imports:
            # imp.module is already resolved to absolute FQN
            imported_modules.add(imp.module)

        result[module_name] = frozenset(imported_modules)

    return MappingProxyType(result)
