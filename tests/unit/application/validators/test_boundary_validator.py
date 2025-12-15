"""Tests for validators/boundary_validator.py."""

import pytest

from archcheck.application.validators.boundary_validator import (
    BoundaryValidator,
    _get_layer,
)
from archcheck.domain.model.configuration import ArchitectureConfig
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from tests.factories import make_merged_graph


class TestGetLayer:
    """Tests for _get_layer helper."""

    def test_extracts_second_component(self) -> None:
        """Layer is second component after root package."""
        assert _get_layer("myapp.domain.model.user") == "domain"
        assert _get_layer("myapp.services.auth") == "services"
        assert _get_layer("myapp.infrastructure.db") == "infrastructure"

    def test_single_component(self) -> None:
        """Single component returns itself."""
        assert _get_layer("myapp") == "myapp"

    def test_two_components(self) -> None:
        """Two components returns second."""
        assert _get_layer("myapp.domain") == "domain"


class TestBoundaryValidatorFromConfig:
    """Tests for BoundaryValidator.from_config."""

    def test_disabled_without_allowed_imports(self) -> None:
        """Returns None if allowed_imports not configured."""
        config = ArchitectureConfig()

        result = BoundaryValidator.from_config(config)

        assert result is None

    def test_enabled_with_allowed_imports(self) -> None:
        """Returns validator if allowed_imports configured."""
        config = ArchitectureConfig(
            allowed_imports={
                "domain": frozenset(),
                "services": frozenset({"domain"}),
            }
        )

        result = BoundaryValidator.from_config(config)

        assert result is not None
        assert isinstance(result, BoundaryValidator)


class TestBoundaryValidatorInit:
    """Tests for BoundaryValidator.__init__."""

    def test_empty_allowed_raises(self) -> None:
        """Raises ValueError if allowed is empty."""
        with pytest.raises(ValueError, match="must not be empty"):
            BoundaryValidator({})


class TestBoundaryValidatorValidate:
    """Tests for BoundaryValidator.validate."""

    def test_allowed_cross_layer_no_violation(self) -> None:
        """Allowed cross-layer calls produce no violations."""
        allowed = {"services": frozenset({"domain"})}
        validator = BoundaryValidator(allowed)
        graph = make_merged_graph(
            internal_edges={
                ("myapp.services.auth.login", "myapp.domain.user.User"): 1,
            },
        )
        config = ArchitectureConfig()

        result = validator.validate(graph, config)

        assert result == ()

    def test_forbidden_cross_layer_violation(self) -> None:
        """Forbidden cross-layer calls produce violations."""
        allowed = {
            "domain": frozenset(),  # domain cannot depend on anything
            "services": frozenset({"domain"}),
        }
        validator = BoundaryValidator(allowed)
        graph = make_merged_graph(
            internal_edges={
                # domain → services is forbidden!
                ("myapp.domain.model.User", "myapp.services.auth.login"): 1,
            },
        )
        config = ArchitectureConfig()

        result = validator.validate(graph, config)

        assert len(result) == 1
        assert "domain" in result[0].message
        assert "services" in result[0].message

    def test_same_layer_always_allowed(self) -> None:
        """Same-layer calls are always allowed."""
        allowed: dict[str, frozenset[str]] = {"domain": frozenset()}
        validator = BoundaryValidator(allowed)
        graph = make_merged_graph(
            internal_edges={
                # domain → domain is always OK
                ("myapp.domain.model.User", "myapp.domain.repository.UserRepo"): 1,
            },
        )
        config = ArchitectureConfig()

        result = validator.validate(graph, config)

        assert result == ()

    def test_unknown_layer_produces_violation(self) -> None:
        """Calls from unknown layer produce violations."""
        allowed = {"services": frozenset({"domain"})}
        validator = BoundaryValidator(allowed)
        graph = make_merged_graph(
            internal_edges={
                # unknown → domain (unknown has no config)
                ("myapp.unknown.module.func", "myapp.domain.model.User"): 1,
            },
        )
        config = ArchitectureConfig()

        result = validator.validate(graph, config)

        # unknown layer has no allowed list → empty frozenset → violation
        assert len(result) == 1

    def test_empty_graph_no_violations(self) -> None:
        """Empty graph produces no violations."""
        allowed: dict[str, frozenset[str]] = {"domain": frozenset()}
        validator = BoundaryValidator(allowed)
        graph = MergedCallGraph.empty()
        config = ArchitectureConfig()

        result = validator.validate(graph, config)

        assert result == ()
