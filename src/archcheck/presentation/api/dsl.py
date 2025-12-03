"""Fluent API (DSL) for architecture testing."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.codebase import Codebase


class ArchCheck:
    """Entry point for architecture analysis."""

    def __init__(self, codebase: Codebase) -> None:
        self._codebase = codebase

    @classmethod
    def analyze(cls, path: str, package: str | None = None) -> ArchCheck:
        """Create analyzer for directory.

        Args:
            path: Path to source directory
            package: Root package name (auto-detected if None)

        Returns:
            ArchCheck instance for fluent API
        """
        raise NotImplementedError("MVP: implement AST parser first")
