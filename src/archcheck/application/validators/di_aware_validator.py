"""DI-aware boundary validator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from archcheck.application.static_analysis.registry import StaticAnalysisRegistry
from archcheck.application.validators._base import BaseValidator
from archcheck.domain.model.enums import RuleCategory, Severity
from archcheck.domain.model.violation import Violation

if TYPE_CHECKING:
    from collections.abc import Mapping

    from archcheck.domain.model.configuration import ArchitectureConfig
    from archcheck.domain.model.function_edge import FunctionEdge
    from archcheck.domain.model.merged_call_graph import MergedCallGraph


class DIAwareValidator(BaseValidator):
    """DI-aware boundary validator.

    Validates layer boundaries while understanding Dependency Injection patterns.
    When a call appears to violate boundaries (e.g., application → infrastructure),
    this validator checks if the callee implements an interface from an allowed layer.

    Example:
        allowed: {"application": {"domain"}}

        Without DI awareness:
            application.UserService → infrastructure.SqlUserRepo  # VIOLATION!

        With DI awareness:
            application.UserService → SqlUserRepo (implements domain.UserRepoProtocol)
            Since UserRepoProtocol is in domain, and domain is allowed, this is OK.

    Attributes:
        _allowed: Map from layer to allowed target layers
        _registry: StaticAnalysisRegistry for interface/impl resolution
        _bypass: Modules that bypass validation (composition root)
    """

    category = RuleCategory.BOUNDARIES

    def __init__(
        self,
        allowed: Mapping[str, frozenset[str]],
        registry: StaticAnalysisRegistry,
        bypass_modules: frozenset[str],
    ) -> None:
        """Initialize DI-aware validator.

        Args:
            allowed: Map from layer name to set of allowed target layer names
            registry: StaticAnalysisRegistry with interface/implementation info
            bypass_modules: Module FQNs that bypass validation (e.g., main.py, di.py)

        Raises:
            TypeError: If any parameter is None (FAIL-FIRST)
        """
        if allowed is None:
            raise TypeError("allowed must not be None")
        if registry is None:
            raise TypeError("registry must not be None")
        if bypass_modules is None:
            raise TypeError("bypass_modules must not be None")

        self._allowed = allowed
        self._registry = registry
        self._bypass = bypass_modules

    def validate(
        self,
        graph: MergedCallGraph,
        config: ArchitectureConfig,
    ) -> tuple[Violation, ...]:
        """Validate layer boundaries with DI awareness.

        Only checks DIRECT edges (boundary-relevant).
        PARAMETRIC, INHERITED, FRAMEWORK edges are already filtered.

        Args:
            graph: MergedCallGraph to validate
            config: Architecture configuration

        Returns:
            Tuple of Violation objects for boundary violations

        Raises:
            TypeError: If graph or config is None (FAIL-FIRST)
        """
        if graph is None:
            raise TypeError("graph must not be None")
        if config is None:
            raise TypeError("config must not be None")

        violations: list[Violation] = []

        # Only check direct_edges (boundary-relevant)
        for edge in graph.direct_edges:
            caller_layer = self._get_layer(edge.caller_fqn)
            callee_layer = self._get_layer(edge.callee_fqn)

            # Skip if can't determine layers
            if caller_layer is None or callee_layer is None:
                continue

            # Same layer OK
            if caller_layer == callee_layer:
                continue

            # Bypass modules OK (composition root)
            caller_module = self._get_module(edge.caller_fqn)
            if caller_module in self._bypass:
                continue

            # Skip if caller layer has no rules defined
            allowed_for_caller = self._allowed.get(caller_layer)
            if allowed_for_caller is None:
                continue

            # Direct allowed?
            if callee_layer in allowed_for_caller:
                continue

            # DI pattern: callee implements interface from allowed layer?
            if self._is_di_allowed(edge.callee_fqn, allowed_for_caller):
                continue

            # Violation detected
            violations.append(
                self._make_violation(
                    edge=edge,
                    caller_layer=caller_layer,
                    callee_layer=callee_layer,
                )
            )

        return tuple(violations)

    def _is_di_allowed(
        self,
        callee_fqn: str,
        allowed_layers: frozenset[str],
    ) -> bool:
        """Check if callee implements interface from allowed layer.

        Args:
            callee_fqn: FQN of the callee (might be class or method)
            allowed_layers: Layers allowed for the caller

        Returns:
            True if callee implements interface from allowed layer
        """
        # Extract class FQN from method FQN if needed
        class_fqn = self._extract_class_fqn(callee_fqn)
        if class_fqn is None:
            return False

        # Get interfaces implemented by this class
        interfaces = self._registry.get_implemented_interfaces(class_fqn)
        if not interfaces:
            return False

        # Check if any interface is from allowed layer
        for interface_fqn in interfaces:
            interface_layer = self._get_layer_from_fqn(interface_fqn)
            if interface_layer in allowed_layers:
                return True

        return False

    def _extract_class_fqn(self, fqn: str) -> str | None:
        """Extract class FQN from method FQN.

        Args:
            fqn: Fully qualified name (might be module.Class.method or module.Class)

        Returns:
            Class FQN or None if can't determine
        """
        # Try direct lookup first (fqn is already a class)
        if self._registry.is_implementation(fqn):
            return fqn

        # Try removing last component (method name)
        parts = fqn.rsplit(".", 1)
        if len(parts) == 2:
            potential_class = parts[0]
            if self._registry.is_implementation(potential_class):
                return potential_class

        return None

    def _get_layer(self, fqn: str) -> str | None:
        """Extract layer name from FQN using naming convention.

        Assumes FQN pattern: package.layer.module.Class
        Layer is the second component.

        Args:
            fqn: Fully qualified name

        Returns:
            Layer name or None if FQN too short
        """
        parts = fqn.split(".")
        if len(parts) < 2:
            return None

        # Second component is the layer
        return parts[1]

    def _get_layer_from_fqn(self, fqn: str) -> str | None:
        """Extract layer from FQN using naming convention.

        Assumes FQN like: package.layer.module.Class
        Layer is second component.

        Args:
            fqn: Fully qualified name

        Returns:
            Layer name or None
        """
        parts = fqn.split(".")
        if len(parts) >= 2:
            return parts[1]  # Assume second component is layer
        return None

    def _get_module(self, fqn: str) -> str:
        """Extract module from FQN.

        Args:
            fqn: Fully qualified name

        Returns:
            Module part (everything before last dot for function, or up to class for method)
        """
        # For class.method, return class's module
        parts = fqn.rsplit(".", 2)
        if len(parts) >= 2:
            return ".".join(parts[:-1])
        return fqn

    def _make_violation(
        self,
        edge: FunctionEdge,
        caller_layer: str,
        callee_layer: str,
    ) -> Violation:
        """Create a Violation for boundary breach.

        Args:
            edge: FunctionEdge that violates boundary
            caller_layer: Caller's layer
            callee_layer: Callee's layer

        Returns:
            Violation object with real location from edge.first_location
        """
        allowed = self._allowed.get(caller_layer, frozenset())
        return Violation(
            rule_name="di_aware_boundary",
            message=f"Layer '{caller_layer}' cannot depend on '{callee_layer}'",
            location=edge.first_location,
            severity=Severity.ERROR,
            category=RuleCategory.BOUNDARIES,
            subject=f"{edge.caller_fqn} → {edge.callee_fqn}",
            expected=f"Imports from: {sorted(allowed)}",
            actual=f"Import from: {callee_layer}",
            suggestion="Use DI pattern with interface from allowed layer",
        )

    @classmethod
    def from_config(
        cls,
        config: ArchitectureConfig,
        registry: object | None = None,
    ) -> Self | None:
        """Create validator from configuration.

        Args:
            config: Architecture configuration
            registry: StaticAnalysisRegistry (required for DI-aware validation)

        Returns:
            DIAwareValidator instance or None if not configured
        """
        if config.allowed_imports is None:
            return None
        if not isinstance(registry, StaticAnalysisRegistry):
            return None

        bypass = config.composition_root or frozenset()
        return cls(config.allowed_imports, registry, bypass)
