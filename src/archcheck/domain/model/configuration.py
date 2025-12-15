"""Architecture configuration for Layer 2 (user config).

This is the user-provided configuration that enables/disables validators.
None = feature disabled, value = feature enabled with that config.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ArchitectureConfig:
    """Layer 2 configuration DTO.

    Immutable configuration object with FAIL-FIRST validation.
    None = feature disabled, value = feature enabled.

    User provides this to configure which validators are active
    and with what parameters.

    Attributes:
        # Boundaries (BoundaryValidator, DIAwareValidator)
        allowed_imports: Layer → allowed layers mapping. None = disabled.
        pure_layers: Layers that must not have side effects. None = disabled.
        allowed_external: Allowed external packages. None = all allowed.
        composition_root: Modules that bypass DI checks. None = disabled.

        # Edge Classification (EdgeClassifier)
        known_frameworks: Framework package prefixes (pytest, fastapi, etc.).
            Used to classify FRAMEWORK edges. None = use empty set.

        # Coupling (CouplingValidator)
        max_fan_out: Max outgoing dependencies per function. None = disabled.
        max_constructor_deps: Max DI deps in constructor. None = disabled.
        stable_layers: Layers that must be stable (low instability). None = disabled.

        # Cohesion (CohesionValidator)
        max_class_methods: Max public methods per class. None = disabled.
        max_protocol_methods: Max methods in Protocol. None = disabled.

        # Coverage
        dead_code_whitelist: FQN patterns to ignore in dead code. None = disabled.
        coverage_threshold: Min coverage percent (0-100). None = disabled.

        # Reporting
        lib_tags: Library → tag mapping for grouping. None = disabled.
        entry_point_patterns: Category → patterns mapping. None = use defaults.

        # User extensions (for custom validators)
        extras: Arbitrary user data for custom validators.
    """

    # Boundaries
    allowed_imports: Mapping[str, frozenset[str]] | None = None
    pure_layers: frozenset[str] | None = None
    allowed_external: frozenset[str] | None = None
    composition_root: frozenset[str] | None = None

    # Edge Classification (EdgeClassifier)
    known_frameworks: frozenset[str] | None = None

    # Coupling
    max_fan_out: int | None = None
    max_constructor_deps: int | None = None
    stable_layers: frozenset[str] | None = None

    # Cohesion
    max_class_methods: int | None = None
    max_protocol_methods: int | None = None

    # Coverage
    dead_code_whitelist: frozenset[str] | None = None
    coverage_threshold: float | None = None

    # Reporting
    lib_tags: Mapping[str, str] | None = None
    entry_point_patterns: Mapping[str, tuple[str, ...]] | None = None

    # User extensions
    extras: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        # max_fan_out must be >= 1 if set
        if self.max_fan_out is not None and self.max_fan_out < 1:
            raise ValueError(f"max_fan_out must be >= 1, got {self.max_fan_out}")

        # max_constructor_deps must be >= 0 if set
        if self.max_constructor_deps is not None and self.max_constructor_deps < 0:
            raise ValueError(f"max_constructor_deps must be >= 0, got {self.max_constructor_deps}")

        # max_class_methods must be >= 1 if set
        if self.max_class_methods is not None and self.max_class_methods < 1:
            raise ValueError(f"max_class_methods must be >= 1, got {self.max_class_methods}")

        # max_protocol_methods must be >= 1 if set
        if self.max_protocol_methods is not None and self.max_protocol_methods < 1:
            raise ValueError(f"max_protocol_methods must be >= 1, got {self.max_protocol_methods}")

        # coverage_threshold must be 0-100 if set
        if self.coverage_threshold is not None:
            if not 0.0 <= self.coverage_threshold <= 100.0:
                raise ValueError(f"coverage_threshold must be 0-100, got {self.coverage_threshold}")

        # pure_layers must be subset of allowed_imports keys if both set
        if self.pure_layers is not None and self.allowed_imports is not None:
            unknown = self.pure_layers - frozenset(self.allowed_imports.keys())
            if unknown:
                raise ValueError(f"pure_layers contains unknown layers: {unknown}")

        # stable_layers must be subset of allowed_imports keys if both set
        if self.stable_layers is not None and self.allowed_imports is not None:
            unknown = self.stable_layers - frozenset(self.allowed_imports.keys())
            if unknown:
                raise ValueError(f"stable_layers contains unknown layers: {unknown}")

    def has_boundary_config(self) -> bool:
        """Check if boundary validation is configured."""
        return self.allowed_imports is not None

    def has_purity_config(self) -> bool:
        """Check if purity validation is configured."""
        return self.pure_layers is not None

    def has_coupling_config(self) -> bool:
        """Check if coupling validation is configured."""
        return self.max_fan_out is not None or self.stable_layers is not None

    def has_cohesion_config(self) -> bool:
        """Check if cohesion validation is configured."""
        return self.max_class_methods is not None or self.max_protocol_methods is not None

    def has_coverage_config(self) -> bool:
        """Check if coverage validation is configured."""
        return self.coverage_threshold is not None
