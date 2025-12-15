"""Tests for ResolvedClass domain type."""

import pytest

from archcheck.domain.model.resolved_class import ResolvedClass


class TestResolvedClassCreation:
    """Test ResolvedClass creation."""

    def test_create_protocol_class(self) -> None:
        """Create a Protocol interface."""
        rc = ResolvedClass(
            fqn="myapp.domain.ports.UserRepository",
            raw_bases=("Protocol",),
            resolved_bases=("typing.Protocol",),
            is_protocol=True,
            is_abc=False,
            interface_methods=frozenset({"get", "save", "delete"}),
        )
        assert rc.fqn == "myapp.domain.ports.UserRepository"
        assert rc.is_protocol is True
        assert rc.is_abc is False
        assert rc.interface_methods == {"get", "save", "delete"}

    def test_create_abc_class(self) -> None:
        """Create an ABC interface."""
        rc = ResolvedClass(
            fqn="myapp.domain.base.BaseService",
            raw_bases=("ABC",),
            resolved_bases=("abc.ABC",),
            is_protocol=False,
            is_abc=True,
            interface_methods=frozenset({"process"}),
        )
        assert rc.is_abc is True
        assert rc.is_protocol is False

    def test_create_implementation(self) -> None:
        """Create an implementation class."""
        rc = ResolvedClass(
            fqn="myapp.infrastructure.repos.SqlUserRepository",
            raw_bases=("UserRepository",),
            resolved_bases=("myapp.domain.ports.UserRepository",),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.is_protocol is False
        assert rc.is_abc is False
        assert len(rc.interface_methods) == 0

    def test_create_multiple_bases(self) -> None:
        """Create class with multiple bases."""
        rc = ResolvedClass(
            fqn="myapp.services.ComplexService",
            raw_bases=("BaseService", "LoggingMixin", "Cacheable"),
            resolved_bases=(
                "myapp.base.BaseService",
                "myapp.mixins.LoggingMixin",
                "myapp.cache.Cacheable",
            ),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert len(rc.raw_bases) == 3
        assert len(rc.resolved_bases) == 3

    def test_create_no_bases(self) -> None:
        """Create class with no bases."""
        rc = ResolvedClass(
            fqn="myapp.models.Simple",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.raw_bases == ()
        assert rc.resolved_bases == ()


class TestResolvedClassValidation:
    """Test FAIL-FIRST validation."""

    def test_empty_fqn_fails(self) -> None:
        """Empty fqn raises ValueError."""
        with pytest.raises(ValueError, match="fqn must not be empty"):
            ResolvedClass(
                fqn="",
                raw_bases=(),
                resolved_bases=(),
                is_protocol=False,
                is_abc=False,
                interface_methods=frozenset(),
            )

    def test_mismatched_bases_length_fails(self) -> None:
        """Different lengths of raw_bases and resolved_bases raises ValueError."""
        with pytest.raises(ValueError, match="same length"):
            ResolvedClass(
                fqn="myapp.SomeClass",
                raw_bases=("Base1", "Base2"),
                resolved_bases=("only.One",),
                is_protocol=False,
                is_abc=False,
                interface_methods=frozenset(),
            )


class TestResolvedClassProperties:
    """Test computed properties."""

    def test_is_interface_true_for_protocol(self) -> None:
        """is_interface returns True for Protocol."""
        rc = ResolvedClass(
            fqn="myapp.Port",
            raw_bases=("Protocol",),
            resolved_bases=("typing.Protocol",),
            is_protocol=True,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.is_interface is True

    def test_is_interface_true_for_abc(self) -> None:
        """is_interface returns True for ABC."""
        rc = ResolvedClass(
            fqn="myapp.Base",
            raw_bases=("ABC",),
            resolved_bases=("abc.ABC",),
            is_protocol=False,
            is_abc=True,
            interface_methods=frozenset(),
        )
        assert rc.is_interface is True

    def test_is_interface_false_for_impl(self) -> None:
        """is_interface returns False for implementation."""
        rc = ResolvedClass(
            fqn="myapp.Impl",
            raw_bases=("Port",),
            resolved_bases=("myapp.Port",),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.is_interface is False

    def test_module_extraction(self) -> None:
        """module property extracts module from FQN."""
        rc = ResolvedClass(
            fqn="myapp.domain.ports.UserRepo",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.module == "myapp.domain.ports"

    def test_module_single_part(self) -> None:
        """module for single-part FQN."""
        rc = ResolvedClass(
            fqn="TopLevel",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.module == ""

    def test_name_extraction(self) -> None:
        """name property extracts class name from FQN."""
        rc = ResolvedClass(
            fqn="myapp.domain.ports.UserRepo",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.name == "UserRepo"

    def test_has_abstract_methods_true(self) -> None:
        """has_abstract_methods True when methods present."""
        rc = ResolvedClass(
            fqn="myapp.Port",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=True,
            is_abc=False,
            interface_methods=frozenset({"process", "validate"}),
        )
        assert rc.has_abstract_methods is True

    def test_has_abstract_methods_false(self) -> None:
        """has_abstract_methods False when no methods."""
        rc = ResolvedClass(
            fqn="myapp.Impl",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.has_abstract_methods is False


class TestResolvedClassImplements:
    """Test implements method."""

    def test_implements_returns_true(self) -> None:
        """implements returns True when interface in resolved_bases."""
        rc = ResolvedClass(
            fqn="myapp.infra.SqlRepo",
            raw_bases=("UserRepo",),
            resolved_bases=("myapp.ports.UserRepo",),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.implements("myapp.ports.UserRepo") is True

    def test_implements_returns_false(self) -> None:
        """implements returns False when interface not in resolved_bases."""
        rc = ResolvedClass(
            fqn="myapp.infra.SqlRepo",
            raw_bases=("UserRepo",),
            resolved_bases=("myapp.ports.UserRepo",),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.implements("myapp.ports.OrderRepo") is False

    def test_implements_multiple_interfaces(self) -> None:
        """implements works with multiple resolved bases."""
        rc = ResolvedClass(
            fqn="myapp.infra.CombinedRepo",
            raw_bases=("UserRepo", "OrderRepo"),
            resolved_bases=("myapp.ports.UserRepo", "myapp.ports.OrderRepo"),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc.implements("myapp.ports.UserRepo") is True
        assert rc.implements("myapp.ports.OrderRepo") is True
        assert rc.implements("myapp.ports.Other") is False


class TestResolvedClassStr:
    """Test string representation."""

    def test_str_interface(self) -> None:
        """String format for interface."""
        rc = ResolvedClass(
            fqn="myapp.ports.UserRepo",
            raw_bases=("Protocol",),
            resolved_bases=("typing.Protocol",),
            is_protocol=True,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert str(rc) == "myapp.ports.UserRepo (interface) [1 bases]"

    def test_str_impl(self) -> None:
        """String format for implementation."""
        rc = ResolvedClass(
            fqn="myapp.infra.SqlRepo",
            raw_bases=("UserRepo", "Cacheable"),
            resolved_bases=("myapp.ports.UserRepo", "myapp.cache.Cacheable"),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert str(rc) == "myapp.infra.SqlRepo (impl) [2 bases]"


class TestResolvedClassImmutability:
    """Test frozen dataclass behavior."""

    def test_cannot_modify_fqn(self) -> None:
        """Attempting to modify fqn raises FrozenInstanceError."""
        rc = ResolvedClass(
            fqn="myapp.Class",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        with pytest.raises(AttributeError):
            rc.fqn = "other"  # type: ignore[misc]

    def test_cannot_modify_is_protocol(self) -> None:
        """Attempting to modify is_protocol raises FrozenInstanceError."""
        rc = ResolvedClass(
            fqn="myapp.Class",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        with pytest.raises(AttributeError):
            rc.is_protocol = True  # type: ignore[misc]


class TestResolvedClassEquality:
    """Test equality and hashing."""

    def test_equal_classes(self) -> None:
        """Identical resolved classes are equal."""
        rc1 = ResolvedClass(
            fqn="myapp.Class",
            raw_bases=("Base",),
            resolved_bases=("myapp.Base",),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        rc2 = ResolvedClass(
            fqn="myapp.Class",
            raw_bases=("Base",),
            resolved_bases=("myapp.Base",),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc1 == rc2

    def test_different_fqn(self) -> None:
        """Different fqn means not equal."""
        rc1 = ResolvedClass(
            fqn="myapp.Class1",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        rc2 = ResolvedClass(
            fqn="myapp.Class2",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        assert rc1 != rc2

    def test_hashable(self) -> None:
        """ResolvedClass is hashable for use in sets."""
        rc = ResolvedClass(
            fqn="myapp.Class",
            raw_bases=(),
            resolved_bases=(),
            is_protocol=False,
            is_abc=False,
            interface_methods=frozenset(),
        )
        rc_set = {rc}
        assert rc in rc_set
