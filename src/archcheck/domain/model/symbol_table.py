"""Symbol table for name resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.import_ import Import


@dataclass(slots=True)
class SymbolTable:
    """Tracks imported names for resolution.

    Mutable - filled during parsing.

    Handles:
    - import X
    - import X as Y
    - from X import Y
    - from X import Y as Z
    - from X import * (star imports) — LIMITATION below

    LIMITATION: Star imports resolution is BEST EFFORT.
    We cannot know which names are actually exported by star-imported module
    without executing/analyzing that module. We return None for star imports
    and track them separately via has_star_imports() for violation reporting.

    Attributes:
        _direct: Local name → fully qualified name mapping
        _star_modules: Modules from which * was imported
    """

    _direct: dict[str, str] = field(default_factory=dict)
    _star_modules: list[str] = field(default_factory=list)

    def add_import(self, imp: Import) -> None:
        """Register import in symbol table.

        Args:
            imp: Import to register

        Raises:
            ValueError: If imp.name is empty string (not None)
        """
        # Handle star import
        if imp.name == "*":
            self._star_modules.append(imp.module)
            return

        # FAIL-FIRST: empty name string is invalid (None is ok)
        if imp.name is not None and imp.name == "":
            raise ValueError("import name must be non-empty string or None")

        local_name = imp.imported_name
        if imp.name is not None:
            qualified = f"{imp.module}.{imp.name}"
        else:
            qualified = imp.module

        self._direct[local_name] = qualified

    def resolve(self, name: str) -> str | None:
        """Resolve local name to fully qualified name.

        Args:
            name: Local name to resolve (may include dots for attr access)

        Returns:
            Fully qualified name if found in direct imports.
            None if unresolved OR if name might come from star import.

        Note:
            Does NOT guess star import sources. Use has_star_imports()
            to check if unresolved name might come from star import.
        """
        # FAIL-FIRST: empty name
        if not name:
            raise ValueError("name must not be empty")

        # 1. Direct match: name is imported directly
        if name in self._direct:
            return self._direct[name]

        # 2. Attribute chain: resolve first part, append rest
        # e.g., "os.path.join" → resolve("os") + ".path.join"
        if "." in name:
            first, rest = name.split(".", 1)
            if first in self._direct:
                return f"{self._direct[first]}.{rest}"

        # 3. NOT guessing star imports - return None
        # Caller should check has_star_imports() if resolution matters
        return None

    def has_star_imports(self) -> bool:
        """Check if module has star imports.

        Star imports are anti-pattern. If has_star_imports() is True
        and resolve() returns None, the name might come from star import.
        """
        return len(self._star_modules) > 0

    @property
    def star_import_modules(self) -> tuple[str, ...]:
        """Modules with star imports (for violation reporting)."""
        return tuple(self._star_modules)

    def all_names(self) -> frozenset[str]:
        """Get all locally available names (excluding star imports)."""
        return frozenset(self._direct.keys())

    @property
    def size(self) -> int:
        """Total number of direct imports."""
        return len(self._direct)
