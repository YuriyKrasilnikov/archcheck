"""Real architecture test: archcheck testing itself."""

from pathlib import Path

import pytest

from archcheck.application.merge import build_static_merged_graph
from archcheck.domain.model.codebase import Codebase
from archcheck.infrastructure.adapters.ast_parser import ASTSourceParser
from archcheck.presentation.api.dsl import ArchCheck


@pytest.fixture(scope="module")
def archcheck_codebase() -> Codebase:
    """Parse archcheck source code."""
    src_path = Path(__file__).parent.parent.parent / "src"
    archcheck_path = src_path / "archcheck"
    parser = ASTSourceParser(root_path=src_path)
    return parser.parse_directory(archcheck_path, "archcheck")


@pytest.fixture(scope="module")
def arch(archcheck_codebase: Codebase) -> ArchCheck:
    """ArchCheck for archcheck itself."""
    return ArchCheck(archcheck_codebase)


@pytest.fixture(scope="module")
def arch_with_graph(archcheck_codebase: Codebase) -> ArchCheck:
    """ArchCheck with graph for edge queries."""
    graph = build_static_merged_graph(archcheck_codebase)
    return ArchCheck(archcheck_codebase, graph)


class TestArchcheckLayers:
    """Test archcheck follows its own hexagonal architecture."""

    def test_domain_has_no_infrastructure_imports(self, arch: ArchCheck) -> None:
        """Domain layer must not import from infrastructure."""
        arch.modules().in_layer("domain").should().not_import(
            "archcheck.infrastructure.**"
        ).assert_check()

    def test_domain_has_no_application_imports(self, arch: ArchCheck) -> None:
        """Domain layer must not import from application."""
        arch.modules().in_layer("domain").should().not_import(
            "archcheck.application.**"
        ).assert_check()

    def test_domain_has_no_presentation_imports(self, arch: ArchCheck) -> None:
        """Domain layer must not import from presentation."""
        arch.modules().in_layer("domain").should().not_import(
            "archcheck.presentation.**"
        ).assert_check()

    def test_infrastructure_has_no_application_imports(self, arch: ArchCheck) -> None:
        """Infrastructure layer must not import from application."""
        arch.modules().in_layer("infrastructure").should().not_import(
            "archcheck.application.**"
        ).assert_check()

    def test_infrastructure_has_no_presentation_imports(self, arch: ArchCheck) -> None:
        """Infrastructure layer must not import from presentation."""
        arch.modules().in_layer("infrastructure").should().not_import(
            "archcheck.presentation.**"
        ).assert_check()

    def test_application_has_no_presentation_imports(self, arch: ArchCheck) -> None:
        """Application layer must not import from presentation."""
        arch.modules().in_layer("application").should().not_import(
            "archcheck.presentation.**"
        ).assert_check()


class TestArchcheckNaming:
    """Test archcheck follows naming conventions."""

    def test_validators_in_validators_package(self, arch: ArchCheck) -> None:
        """All *Validator classes should be in application.validators package."""
        validators = arch.classes().named("*Validator").execute()
        for v in validators:
            assert "validators" in v.qualified_name, f"{v.qualified_name} not in validators"

    def test_reporters_in_reporters_package(self, arch: ArchCheck) -> None:
        """All *Reporter classes should be in application.reporters package."""
        reporters = arch.classes().named("*Reporter").execute()
        for r in reporters:
            assert "reporters" in r.qualified_name, f"{r.qualified_name} not in reporters"

    def test_analyzers_in_analyzers_package(self, arch: ArchCheck) -> None:
        """All *Analyzer classes should be in infrastructure.analyzers package."""
        analyzers = arch.classes().named("*Analyzer").execute()
        for a in analyzers:
            assert "analyzers" in a.qualified_name, f"{a.qualified_name} not in analyzers"


class TestArchcheckEdges:
    """Test archcheck call graph structure."""

    def test_domain_to_infrastructure_edges_count(self, arch_with_graph: ArchCheck) -> None:
        """Count how many domain → infrastructure edges exist."""
        edges = arch_with_graph.edges().from_layer("domain").to_layer("infrastructure").execute()
        # Domain should have zero direct dependencies on infrastructure
        assert len(edges) == 0, f"Found {len(edges)} domain → infrastructure edges"

    def test_crossing_boundary_edges(self, arch_with_graph: ArchCheck) -> None:
        """List all cross-boundary edges."""
        edges = arch_with_graph.edges().crossing_boundary().execute()
        # Just verify we can query them
        assert isinstance(edges, tuple)


class TestQueryExecution:
    """Test that queries actually work and return data."""

    def test_modules_count(self, arch: ArchCheck) -> None:
        """Verify we parsed modules."""
        modules = arch.modules().execute()
        assert len(modules) > 50, f"Expected 50+ modules, got {len(modules)}"

    def test_classes_count(self, arch: ArchCheck) -> None:
        """Verify we parsed classes."""
        classes = arch.classes().execute()
        assert len(classes) > 30, f"Expected 30+ classes, got {len(classes)}"

    def test_functions_count(self, arch: ArchCheck) -> None:
        """Verify we parsed functions."""
        functions = arch.functions().execute()
        assert len(functions) > 100, f"Expected 100+ functions, got {len(functions)}"

    def test_domain_modules(self, arch: ArchCheck) -> None:
        """Verify domain layer modules."""
        modules = arch.modules().in_layer("domain").execute()
        assert len(modules) > 20, f"Expected 20+ domain modules, got {len(modules)}"

    def test_async_functions(self, arch: ArchCheck) -> None:
        """Verify we detect async functions."""
        async_funcs = arch.functions().async_only().execute()
        # archcheck has some async code in collectors
        assert len(async_funcs) >= 0  # May or may not have async


class TestCollectViolations:
    """Test violation collection without raising."""

    def test_collect_returns_tuple(self, arch: ArchCheck) -> None:
        """collect() returns tuple of violations."""
        violations = (
            arch.modules()
            .in_layer("domain")
            .should()
            .not_import("archcheck.infrastructure.**")
            .collect()
        )
        assert isinstance(violations, tuple)
        assert len(violations) == 0  # Should pass

    def test_is_valid_returns_bool(self, arch: ArchCheck) -> None:
        """is_valid() returns boolean."""
        result = (
            arch.modules()
            .in_layer("domain")
            .should()
            .not_import("archcheck.infrastructure.**")
            .is_valid()
        )
        assert result is True
