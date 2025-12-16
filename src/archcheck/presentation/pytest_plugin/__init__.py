"""pytest plugin for archcheck.

Provides fixtures for architecture testing:
    arch_codebase: Parsed codebase from source directory
    arch_config: Architecture configuration (override in conftest.py)
    arch: Fluent DSL entry point (ArchCheck, static-only)
    arch_merged_graph: Static-only MergedCallGraph
    arch_with_graph: ArchCheck with edge support
    arch_checker: ArchChecker facade for graph-level validation

Configuration (pytest.ini or pyproject.toml):
    arch_source_dir: Source directory to analyze (default: "src")
    arch_package: Root package name (default: directory name)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Register fixtures from fixtures module
from archcheck.presentation.pytest_plugin.fixtures import (
    arch,
    arch_checker,
    arch_codebase,
    arch_config,
    arch_merged_graph,
    arch_with_graph,
)

if TYPE_CHECKING:
    import pytest

# Export fixtures for pytest discovery
__all__ = [
    "arch",
    "arch_checker",
    "arch_codebase",
    "arch_config",
    "arch_merged_graph",
    "arch_with_graph",
]


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest plugin with markers and ini options."""
    # Add marker for architecture tests
    config.addinivalue_line(
        "markers",
        "arch: mark test as architecture test",
    )
