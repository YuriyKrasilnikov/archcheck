"""Architecture definition entities.

Provides immutable architecture definitions with Builder pattern for construction.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Self


@dataclass(frozen=True, slots=True)
class Layer:
    """Architecture layer definition.

    Immutable value object with FAIL-FIRST validation.

    Attributes:
        name: Layer name (must not be empty)
        modules: Module patterns (glob, must have at least one)
        may_depend_on: Allowed layer dependencies
        should_not_depend_on: Forbidden layer dependencies
        allowed_external: Allowed external packages
        forbidden_external: Forbidden external packages
    """

    name: str
    modules: frozenset[str]
    may_depend_on: frozenset[str] = field(default_factory=frozenset)
    should_not_depend_on: frozenset[str] = field(default_factory=frozenset)
    allowed_external: frozenset[str] = field(default_factory=frozenset)
    forbidden_external: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.name:
            raise ValueError("layer name must not be empty")
        if not self.modules:
            raise ValueError("layer must have at least one module pattern")

        overlap = self.may_depend_on & self.should_not_depend_on
        if overlap:
            raise ValueError(f"layer cannot both allow and forbid dependency on: {overlap}")

        external_overlap = self.allowed_external & self.forbidden_external
        if external_overlap:
            raise ValueError(f"layer cannot both allow and forbid external: {external_overlap}")


@dataclass(frozen=True, slots=True)
class Component:
    """Hexagonal architecture component.

    Immutable value object with FAIL-FIRST validation.

    Attributes:
        name: Component name (must not be empty)
        modules: Module patterns (must have at least one)
        ports: Interface patterns (ABCs)
        adapters: Implementation patterns
    """

    name: str
    modules: frozenset[str]
    ports: frozenset[str] = field(default_factory=frozenset)
    adapters: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.name:
            raise ValueError("component name must not be empty")
        if not self.modules:
            raise ValueError("component must have at least one module pattern")


@dataclass(frozen=True, slots=True)
class ArchitectureDefinition:
    """Project architecture definition.

    Immutable aggregate with FAIL-FIRST validation.
    Use ArchitectureDefinitionBuilder for construction.

    Attributes:
        name: Architecture type (hexagonal, clean, layered, custom)
        layers: Immutable layer name -> Layer mapping
        components: Immutable component name -> Component mapping
        no_circular_dependencies: Forbid circular dependencies
        strict_layer_order: Layers can only depend downward
    """

    name: str
    layers: Mapping[str, Layer] = field(default_factory=dict)
    components: Mapping[str, Component] = field(default_factory=dict)
    no_circular_dependencies: bool = True
    strict_layer_order: bool = True

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.name:
            raise ValueError("architecture name must not be empty")

    def get_layer(self, name: str) -> Layer | None:
        """Get layer by name. Returns None if not found."""
        return self.layers.get(name)

    def get_component(self, name: str) -> Component | None:
        """Get component by name. Returns None if not found."""
        return self.components.get(name)

    @property
    def layer_names(self) -> frozenset[str]:
        """Get all layer names."""
        return frozenset(self.layers.keys())

    @property
    def component_names(self) -> frozenset[str]:
        """Get all component names."""
        return frozenset(self.components.keys())


class ArchitectureDefinitionBuilder:
    """Builder for ArchitectureDefinition.

    Provides fluent API for constructing immutable ArchitectureDefinition.
    FAIL-FIRST: validates on build(), not during construction.

    Example:
        arch = (
            ArchitectureDefinitionBuilder("hexagonal")
            .add_layer(Layer(name="domain", modules=frozenset({"app.domain.**"})))
            .add_layer(Layer(name="infra", modules=frozenset({"app.infra.**"})))
            .add_component(Component(name="core", modules=frozenset({"app.core.**"})))
            .no_circular_dependencies(True)
            .build()
        )
    """

    def __init__(self, name: str) -> None:
        """Initialize builder with architecture name.

        Args:
            name: Architecture type name (hexagonal, clean, layered, custom)
        """
        self._name = name
        self._layers: dict[str, Layer] = {}
        self._components: dict[str, Component] = {}
        self._no_circular_dependencies = True
        self._strict_layer_order = True

    def add_layer(self, layer: Layer) -> Self:
        """Add layer to architecture.

        Args:
            layer: Layer to add

        Returns:
            Self for chaining

        Raises:
            ValueError: If layer with same name already added
        """
        if layer.name in self._layers:
            raise ValueError(f"layer '{layer.name}' already exists")
        self._layers[layer.name] = layer
        return self

    def add_component(self, component: Component) -> Self:
        """Add component to architecture.

        Args:
            component: Component to add

        Returns:
            Self for chaining

        Raises:
            ValueError: If component with same name already added
        """
        if component.name in self._components:
            raise ValueError(f"component '{component.name}' already exists")
        self._components[component.name] = component
        return self

    def no_circular_dependencies(self, value: bool) -> Self:
        """Set circular dependencies policy.

        Args:
            value: True to forbid circular dependencies

        Returns:
            Self for chaining
        """
        self._no_circular_dependencies = value
        return self

    def strict_layer_order(self, value: bool) -> Self:
        """Set strict layer order policy.

        Args:
            value: True to enforce layers can only depend downward

        Returns:
            Self for chaining
        """
        self._strict_layer_order = value
        return self

    def build(self) -> ArchitectureDefinition:
        """Build immutable ArchitectureDefinition.

        Returns:
            Immutable ArchitectureDefinition

        Raises:
            ValueError: If architecture is invalid (via __post_init__)
        """
        return ArchitectureDefinition(
            name=self._name,
            layers=self._layers,
            components=self._components,
            no_circular_dependencies=self._no_circular_dependencies,
            strict_layer_order=self._strict_layer_order,
        )
