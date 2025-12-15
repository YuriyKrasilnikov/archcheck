"""Tests for domain/model/architecture.py."""

from dataclasses import FrozenInstanceError

import pytest

from archcheck.domain.model.architecture import (
    ArchitectureDefinition,
    ArchitectureDefinitionBuilder,
    Component,
    Layer,
)


class TestLayerCreation:
    """Tests for valid Layer creation."""

    def test_minimal_valid(self) -> None:
        layer = Layer(name="domain", modules=frozenset(["myapp.domain.*"]))
        assert layer.name == "domain"
        assert layer.modules == frozenset(["myapp.domain.*"])
        assert layer.may_depend_on == frozenset()
        assert layer.should_not_depend_on == frozenset()
        assert layer.allowed_external == frozenset()
        assert layer.forbidden_external == frozenset()

    def test_with_dependencies(self) -> None:
        layer = Layer(
            name="application",
            modules=frozenset(["myapp.application.*"]),
            may_depend_on=frozenset(["domain"]),
        )
        assert layer.may_depend_on == frozenset(["domain"])

    def test_with_forbidden_dependencies(self) -> None:
        layer = Layer(
            name="domain",
            modules=frozenset(["myapp.domain.*"]),
            should_not_depend_on=frozenset(["infrastructure", "presentation"]),
        )
        assert layer.should_not_depend_on == frozenset(["infrastructure", "presentation"])

    def test_with_allowed_external(self) -> None:
        layer = Layer(
            name="domain",
            modules=frozenset(["myapp.domain.*"]),
            allowed_external=frozenset(["typing", "abc", "dataclasses"]),
        )
        assert layer.allowed_external == frozenset(["typing", "abc", "dataclasses"])

    def test_with_forbidden_external(self) -> None:
        layer = Layer(
            name="domain",
            modules=frozenset(["myapp.domain.*"]),
            forbidden_external=frozenset(["django", "sqlalchemy", "requests"]),
        )
        assert layer.forbidden_external == frozenset(["django", "sqlalchemy", "requests"])

    def test_multiple_module_patterns(self) -> None:
        layer = Layer(
            name="domain",
            modules=frozenset(["myapp.domain.*", "myapp.core.*"]),
        )
        assert len(layer.modules) == 2

    def test_is_frozen(self) -> None:
        layer = Layer(name="domain", modules=frozenset(["myapp.domain.*"]))
        with pytest.raises(AttributeError):
            layer.name = "other"  # type: ignore[misc]


class TestLayerFailFirst:
    """Tests for FAIL-FIRST validation in Layer."""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="layer name must not be empty"):
            Layer(name="", modules=frozenset(["myapp.*"]))

    def test_empty_modules_raises(self) -> None:
        with pytest.raises(ValueError, match="layer must have at least one module pattern"):
            Layer(name="domain", modules=frozenset())

    def test_allow_and_forbid_same_layer_raises(self) -> None:
        with pytest.raises(ValueError, match="layer cannot both allow and forbid dependency on"):
            Layer(
                name="application",
                modules=frozenset(["myapp.application.*"]),
                may_depend_on=frozenset(["infrastructure"]),
                should_not_depend_on=frozenset(["infrastructure"]),
            )

    def test_allow_and_forbid_same_external_raises(self) -> None:
        with pytest.raises(ValueError, match="layer cannot both allow and forbid external"):
            Layer(
                name="domain",
                modules=frozenset(["myapp.domain.*"]),
                allowed_external=frozenset(["requests"]),
                forbidden_external=frozenset(["requests"]),
            )


class TestComponentCreation:
    """Tests for valid Component creation."""

    def test_minimal_valid(self) -> None:
        comp = Component(name="auth", modules=frozenset(["myapp.auth.*"]))
        assert comp.name == "auth"
        assert comp.modules == frozenset(["myapp.auth.*"])
        assert comp.ports == frozenset()
        assert comp.adapters == frozenset()

    def test_with_ports(self) -> None:
        comp = Component(
            name="auth",
            modules=frozenset(["myapp.auth.*"]),
            ports=frozenset(["*Port", "*Repository"]),
        )
        assert comp.ports == frozenset(["*Port", "*Repository"])

    def test_with_adapters(self) -> None:
        comp = Component(
            name="auth",
            modules=frozenset(["myapp.auth.*"]),
            adapters=frozenset(["*Adapter", "*Impl"]),
        )
        assert comp.adapters == frozenset(["*Adapter", "*Impl"])

    def test_full_component(self) -> None:
        comp = Component(
            name="users",
            modules=frozenset(["myapp.users.*"]),
            ports=frozenset(["UserRepository", "EmailService"]),
            adapters=frozenset(["SqlUserRepository", "SmtpEmailService"]),
        )
        assert comp.name == "users"
        assert len(comp.ports) == 2
        assert len(comp.adapters) == 2

    def test_is_frozen(self) -> None:
        comp = Component(name="auth", modules=frozenset(["myapp.auth.*"]))
        with pytest.raises(AttributeError):
            comp.name = "other"  # type: ignore[misc]


class TestComponentFailFirst:
    """Tests for FAIL-FIRST validation in Component."""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="component name must not be empty"):
            Component(name="", modules=frozenset(["myapp.*"]))

    def test_empty_modules_raises(self) -> None:
        with pytest.raises(ValueError, match="component must have at least one module pattern"):
            Component(name="auth", modules=frozenset())


class TestArchitectureDefinitionCreation:
    """Tests for valid ArchitectureDefinition creation."""

    def test_minimal_valid(self) -> None:
        arch = ArchitectureDefinition(name="hexagonal")
        assert arch.name == "hexagonal"
        assert arch.layers == {}
        assert arch.components == {}
        assert arch.no_circular_dependencies is True
        assert arch.strict_layer_order is True

    def test_with_flags(self) -> None:
        arch = ArchitectureDefinition(
            name="custom",
            no_circular_dependencies=False,
            strict_layer_order=False,
        )
        assert arch.no_circular_dependencies is False
        assert arch.strict_layer_order is False

    def test_is_frozen(self) -> None:
        """ArchitectureDefinition is immutable (frozen dataclass)."""
        arch = ArchitectureDefinition(name="hexagonal")
        with pytest.raises(FrozenInstanceError):
            arch.name = "clean"  # type: ignore[misc]


class TestArchitectureDefinitionFailFirst:
    """Tests for FAIL-FIRST validation in ArchitectureDefinition."""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="architecture name must not be empty"):
            ArchitectureDefinition(name="")


class TestArchitectureDefinitionBuilderAddLayer:
    """Tests for ArchitectureDefinitionBuilder.add_layer method."""

    def test_add_layer(self) -> None:
        layer = Layer(name="domain", modules=frozenset(["myapp.domain.*"]))
        arch = ArchitectureDefinitionBuilder("hexagonal").add_layer(layer).build()
        assert arch.layers["domain"] == layer

    def test_add_multiple_layers(self) -> None:
        domain = Layer(name="domain", modules=frozenset(["myapp.domain.*"]))
        application = Layer(name="application", modules=frozenset(["myapp.application.*"]))
        arch = (
            ArchitectureDefinitionBuilder("hexagonal")
            .add_layer(domain)
            .add_layer(application)
            .build()
        )
        assert len(arch.layers) == 2
        assert "domain" in arch.layers
        assert "application" in arch.layers

    def test_add_duplicate_layer_raises(self) -> None:
        layer1 = Layer(name="domain", modules=frozenset(["myapp.domain.*"]))
        layer2 = Layer(name="domain", modules=frozenset(["myapp.core.*"]))
        builder = ArchitectureDefinitionBuilder("hexagonal").add_layer(layer1)

        with pytest.raises(ValueError, match="layer 'domain' already exists"):
            builder.add_layer(layer2)


class TestArchitectureDefinitionBuilderAddComponent:
    """Tests for ArchitectureDefinitionBuilder.add_component method."""

    def test_add_component(self) -> None:
        comp = Component(name="auth", modules=frozenset(["myapp.auth.*"]))
        arch = ArchitectureDefinitionBuilder("hexagonal").add_component(comp).build()
        assert arch.components["auth"] == comp

    def test_add_multiple_components(self) -> None:
        auth = Component(name="auth", modules=frozenset(["myapp.auth.*"]))
        users = Component(name="users", modules=frozenset(["myapp.users.*"]))
        arch = (
            ArchitectureDefinitionBuilder("hexagonal")
            .add_component(auth)
            .add_component(users)
            .build()
        )
        assert len(arch.components) == 2
        assert "auth" in arch.components
        assert "users" in arch.components

    def test_add_duplicate_component_raises(self) -> None:
        comp1 = Component(name="auth", modules=frozenset(["myapp.auth.*"]))
        comp2 = Component(name="auth", modules=frozenset(["myapp.authentication.*"]))
        builder = ArchitectureDefinitionBuilder("hexagonal").add_component(comp1)

        with pytest.raises(ValueError, match="component 'auth' already exists"):
            builder.add_component(comp2)
