"""Tests for DIAwareValidator."""

from types import MappingProxyType

import pytest

from archcheck.application.static_analysis.registry import StaticAnalysisRegistry
from archcheck.application.validators.di_aware_validator import DIAwareValidator
from archcheck.domain.model.configuration import ArchitectureConfig
from archcheck.domain.model.implementation_info import ImplementationInfo
from archcheck.domain.model.interface_info import InterfaceInfo
from tests.factories import make_merged_graph


def make_registry(
    interfaces: dict[str, InterfaceInfo] | None = None,
    implementations: dict[str, ImplementationInfo] | None = None,
) -> StaticAnalysisRegistry:
    """Create a StaticAnalysisRegistry for tests."""
    interfaces = interfaces or {}
    implementations = implementations or {}

    # Build reverse index
    impl_by_interface: dict[str, set[str]] = {}
    for impl_fqn, impl_info in implementations.items():
        for iface_fqn in impl_info.implements:
            if iface_fqn not in impl_by_interface:
                impl_by_interface[iface_fqn] = set()
            impl_by_interface[iface_fqn].add(impl_fqn)

    frozen_index = {k: frozenset(v) for k, v in impl_by_interface.items()}

    return StaticAnalysisRegistry(
        interfaces=MappingProxyType(interfaces),
        implementations=MappingProxyType(implementations),
        impl_by_interface=MappingProxyType(frozen_index),
    )


def make_config(
    allowed_imports: dict[str, frozenset[str]] | None = None,
    composition_root: frozenset[str] | None = None,
) -> ArchitectureConfig:
    """Create an ArchitectureConfig for tests."""
    return ArchitectureConfig(
        allowed_imports=MappingProxyType(allowed_imports) if allowed_imports else None,
        composition_root=composition_root,
    )


class TestDIAwareValidatorFailFirst:
    """Test FAIL-FIRST validation."""

    def test_none_allowed_raises(self) -> None:
        """None allowed raises TypeError."""
        registry = make_registry()
        with pytest.raises(TypeError, match="allowed must not be None"):
            DIAwareValidator(None, registry, frozenset())  # type: ignore[arg-type]

    def test_none_registry_raises(self) -> None:
        """None registry raises TypeError."""
        with pytest.raises(TypeError, match="registry must not be None"):
            DIAwareValidator({}, None, frozenset())  # type: ignore[arg-type]

    def test_none_bypass_raises(self) -> None:
        """None bypass_modules raises TypeError."""
        registry = make_registry()
        with pytest.raises(TypeError, match="bypass_modules must not be None"):
            DIAwareValidator({}, registry, None)  # type: ignore[arg-type]

    def test_validate_none_graph_raises(self) -> None:
        """None graph raises TypeError."""
        registry = make_registry()
        validator = DIAwareValidator({}, registry, frozenset())
        config = make_config()
        with pytest.raises(TypeError, match="graph must not be None"):
            validator.validate(None, config)  # type: ignore[arg-type]

    def test_validate_none_config_raises(self) -> None:
        """None config raises TypeError."""
        registry = make_registry()
        validator = DIAwareValidator({}, registry, frozenset())
        graph = make_merged_graph()
        with pytest.raises(TypeError, match="config must not be None"):
            validator.validate(graph, None)  # type: ignore[arg-type]


class TestDIAwareValidatorBasic:
    """Test basic validation logic."""

    def test_empty_graph_no_violations(self) -> None:
        """Empty graph produces no violations."""
        registry = make_registry()
        validator = DIAwareValidator({}, registry, frozenset())
        graph = make_merged_graph()
        config = make_config()

        violations = validator.validate(graph, config)

        assert len(violations) == 0

    def test_same_layer_allowed(self) -> None:
        """Calls within same layer are allowed."""
        registry = make_registry()
        allowed = {"application": frozenset({"domain"})}
        validator = DIAwareValidator(allowed, registry, frozenset())

        # Both in application layer
        graph = make_merged_graph(
            internal_edges={("myapp.application.service", "myapp.application.helper"): 1}
        )
        config = make_config(allowed_imports=allowed)

        violations = validator.validate(graph, config)

        assert len(violations) == 0

    def test_allowed_layer_no_violation(self) -> None:
        """Calls to allowed layers are not violations."""
        registry = make_registry()
        allowed = {"application": frozenset({"domain"})}
        validator = DIAwareValidator(allowed, registry, frozenset())

        # application → domain is allowed
        graph = make_merged_graph(
            internal_edges={("myapp.application.service", "myapp.domain.entity"): 1}
        )
        config = make_config(allowed_imports=allowed)

        violations = validator.validate(graph, config)

        assert len(violations) == 0

    def test_not_allowed_layer_violation(self) -> None:
        """Calls to not-allowed layers are violations."""
        registry = make_registry()
        allowed = {"application": frozenset({"domain"})}
        validator = DIAwareValidator(allowed, registry, frozenset())

        # application → infrastructure NOT allowed
        graph = make_merged_graph(
            internal_edges={("myapp.application.service", "myapp.infrastructure.repo"): 1}
        )
        config = make_config(allowed_imports=allowed)

        violations = validator.validate(graph, config)

        assert len(violations) == 1
        assert "application" in violations[0].message
        assert "infrastructure" in violations[0].message


class TestDIAwareValidatorDI:
    """Test DI-aware validation logic."""

    def test_di_pattern_allowed(self) -> None:
        """Call to impl that implements interface from allowed layer is OK."""
        # Setup: SqlRepo implements domain.UserRepoProtocol
        interface = InterfaceInfo(
            fqn="myapp.domain.UserRepoProtocol",
            module="myapp.domain",
            name="UserRepoProtocol",
            methods=frozenset({"get", "save"}),
        )
        impl = ImplementationInfo(
            fqn="myapp.infrastructure.SqlRepo",
            module="myapp.infrastructure",
            name="SqlRepo",
            implements=frozenset({"myapp.domain.UserRepoProtocol"}),
        )
        registry = make_registry(
            interfaces={"myapp.domain.UserRepoProtocol": interface},
            implementations={"myapp.infrastructure.SqlRepo": impl},
        )

        # application → domain allowed
        allowed = {"application": frozenset({"domain"})}
        validator = DIAwareValidator(allowed, registry, frozenset())

        # application.UserService → infrastructure.SqlRepo
        # This LOOKS like a violation, but SqlRepo implements domain.UserRepoProtocol
        # and domain is allowed for application layer
        graph = make_merged_graph(
            internal_edges={("myapp.application.UserService", "myapp.infrastructure.SqlRepo"): 1}
        )
        config = make_config(allowed_imports=allowed)

        violations = validator.validate(graph, config)

        # Should be allowed via DI pattern
        assert len(violations) == 0

    def test_di_method_call_allowed(self) -> None:
        """Call to method of impl that implements interface from allowed layer is OK."""
        interface = InterfaceInfo(
            fqn="myapp.domain.UserRepoProtocol",
            module="myapp.domain",
            name="UserRepoProtocol",
            methods=frozenset({"get", "save"}),
        )
        impl = ImplementationInfo(
            fqn="myapp.infrastructure.SqlRepo",
            module="myapp.infrastructure",
            name="SqlRepo",
            implements=frozenset({"myapp.domain.UserRepoProtocol"}),
        )
        registry = make_registry(
            interfaces={"myapp.domain.UserRepoProtocol": interface},
            implementations={"myapp.infrastructure.SqlRepo": impl},
        )

        allowed = {"application": frozenset({"domain"})}
        validator = DIAwareValidator(allowed, registry, frozenset())

        # Call to method of impl
        graph = make_merged_graph(
            internal_edges={
                ("myapp.application.UserService", "myapp.infrastructure.SqlRepo.get"): 1
            }
        )
        config = make_config(allowed_imports=allowed)

        violations = validator.validate(graph, config)

        assert len(violations) == 0


class TestDIAwareValidatorBypass:
    """Test bypass module functionality."""

    def test_bypass_module_allowed(self) -> None:
        """Calls from bypass modules are always allowed."""
        registry = make_registry()
        allowed = {"application": frozenset({"domain"})}
        # main.py is in bypass - it's the composition root
        bypass = frozenset({"myapp.main"})
        validator = DIAwareValidator(allowed, registry, bypass)

        # main → infrastructure would normally violate
        graph = make_merged_graph(
            internal_edges={("myapp.main.setup", "myapp.infrastructure.repo"): 1}
        )
        config = make_config(allowed_imports=allowed)

        violations = validator.validate(graph, config)

        # Bypassed - no violation
        assert len(violations) == 0


class TestDIAwareValidatorFromConfig:
    """Test from_config factory method."""

    def test_no_allowed_imports_returns_none(self) -> None:
        """Config without allowed_imports returns None."""
        config = make_config(allowed_imports=None)
        registry = make_registry()

        validator = DIAwareValidator.from_config(config, registry)

        assert validator is None

    def test_no_registry_returns_none(self) -> None:
        """No registry returns None."""
        config = make_config(allowed_imports={"app": frozenset({"domain"})})

        validator = DIAwareValidator.from_config(config, None)

        assert validator is None

    def test_valid_config_creates_validator(self) -> None:
        """Valid config with registry creates validator."""
        config = make_config(
            allowed_imports={"app": frozenset({"domain"})},
            composition_root=frozenset({"main"}),
        )
        registry = make_registry()

        validator = DIAwareValidator.from_config(config, registry)

        assert validator is not None
        assert isinstance(validator, DIAwareValidator)
