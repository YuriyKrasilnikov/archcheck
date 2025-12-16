"""pytest fixtures for architecture testing.

Provides fixtures for architecture analysis in tests.
User overrides arch_config in their conftest.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from archcheck.application.merge import build_static_merged_graph
from archcheck.application.services import ArchChecker
from archcheck.domain.model.configuration import ArchitectureConfig
from archcheck.infrastructure.adapters.ast_parser import ASTSourceParser
from archcheck.presentation.api.dsl import ArchCheck

if TYPE_CHECKING:
    from archcheck.domain.model.codebase import Codebase
    from archcheck.domain.model.merged_call_graph import MergedCallGraph


def _get_ini_value(config: pytest.Config, name: str, default: str) -> str:
    """Get ini value from pytest config with fallback.

    Args:
        config: pytest Config object
        name: ini option name
        default: default value if not set

    Returns:
        String value of ini option
    """
    value = config.getini(name)
    if value:
        return str(value)
    return default


@pytest.fixture(scope="session")
def arch_codebase(request: pytest.FixtureRequest) -> Codebase:
    """Parse codebase from configured source directory.

    Reads arch_source_dir and arch_package from pytest.ini.
    Defaults: arch_source_dir="src", arch_package=directory name.

    Returns:
        Parsed Codebase
    """
    # Get root directory from pytest config
    # Note: rootdir exists on pytest.Config but type stubs may not include it
    root_dir = Path(str(getattr(request.config, "rootdir", ".")))

    source_dir = _get_ini_value(request.config, "arch_source_dir", "src")
    source_path = root_dir / source_dir

    if not source_path.exists():
        raise FileNotFoundError(
            f"arch_source_dir '{source_path}' does not exist. "
            f"Configure arch_source_dir in pytest.ini or pyproject.toml."
        )

    package = _get_ini_value(request.config, "arch_package", source_path.name)

    parser = ASTSourceParser(root_path=source_path)
    return parser.parse_directory(source_path, package)


@pytest.fixture(scope="session")
def arch_config() -> ArchitectureConfig:
    """Default architecture configuration.

    User overrides this fixture in their conftest.py to provide
    custom configuration.

    Returns:
        Empty ArchitectureConfig (defaults only)
    """
    return ArchitectureConfig()


@pytest.fixture(scope="session")
def arch(arch_codebase: Codebase) -> ArchCheck:
    """Fluent DSL entry point for architecture assertions.

    Static analysis only (no call graph edges).
    Use arch_with_graph for edge assertions.

    Returns:
        ArchCheck instance for fluent queries
    """
    return ArchCheck(arch_codebase)


@pytest.fixture(scope="session")
def arch_merged_graph(
    arch_codebase: Codebase,
    arch_config: ArchitectureConfig,
) -> MergedCallGraph:
    """Static-only merged graph for edge assertions.

    Builds MergedCallGraph from static analysis.
    Uses known_frameworks from arch_config.

    Returns:
        MergedCallGraph with static edges
    """
    return build_static_merged_graph(
        arch_codebase,
        arch_config.known_frameworks,
    )


@pytest.fixture(scope="session")
def arch_with_graph(
    arch_codebase: Codebase,
    arch_merged_graph: MergedCallGraph,
) -> ArchCheck:
    """Fluent DSL with edge support.

    Use for edge() queries and assertions.

    Returns:
        ArchCheck instance with MergedCallGraph
    """
    return ArchCheck(arch_codebase, arch_merged_graph)


@pytest.fixture(scope="session")
def arch_checker(
    arch_codebase: Codebase,
    arch_merged_graph: MergedCallGraph,
    arch_config: ArchitectureConfig,
) -> ArchChecker:
    """ArchChecker facade for graph-level validation.

    Runs validators (cycle, boundary, DI-aware) based on config.

    Returns:
        ArchChecker with config-based validators
    """
    return ArchChecker.from_config(
        arch_codebase,
        arch_merged_graph,
        arch_config,
    )
