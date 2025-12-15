"""Tests for StaticAnalysisRegistry."""

from pathlib import Path
from types import MappingProxyType

import pytest

from archcheck.application.static_analysis.registry import StaticAnalysisRegistry
from archcheck.domain.model.class_ import Class
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.implementation_info import ImplementationInfo
from archcheck.domain.model.interface_info import InterfaceInfo
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module
from archcheck.domain.model.resolved_class import ResolvedClass


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_class(name: str, module_name: str) -> Class:
    """Create a minimal Class for tests."""
    return Class(
        name=name,
        qualified_name=f"{module_name}.{name}",
        bases=(),
        decorators=(),
        methods=(),
        attributes=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
    )


def make_resolved_interface(
    fqn: str,
    methods: frozenset[str] = frozenset(),
    is_protocol: bool = True,
) -> ResolvedClass:
    """Create a resolved interface class."""
    return ResolvedClass(
        fqn=fqn,
        raw_bases=("Protocol",) if is_protocol else ("ABC",),
        resolved_bases=("typing.Protocol",) if is_protocol else ("abc.ABC",),
        is_protocol=is_protocol,
        is_abc=not is_protocol,
        interface_methods=methods,
    )


def make_resolved_impl(
    fqn: str,
    implements: tuple[str, ...],
) -> ResolvedClass:
    """Create a resolved implementation class."""
    raw_bases = tuple(impl.rsplit(".", 1)[-1] for impl in implements)
    return ResolvedClass(
        fqn=fqn,
        raw_bases=raw_bases,
        resolved_bases=implements,
        is_protocol=False,
        is_abc=False,
        interface_methods=frozenset(),
    )


def make_module(
    name: str,
    resolved_classes: tuple[ResolvedClass, ...] = (),
) -> Module:
    """Create a Module with resolved_classes."""
    return Module(
        name=name,
        path=Path(f"src/{name.replace('.', '/')}.py"),
        imports=(),
        classes=(),
        functions=(),
        constants=(),
        resolved_classes=resolved_classes,
    )


def make_codebase(*modules: Module) -> Codebase:
    """Create a Codebase from modules."""
    codebase = Codebase(root_path=Path("src"), root_package="myapp")
    for module in modules:
        codebase.add_module(module)
    return codebase


class TestStaticAnalysisRegistryCreation:
    """Test registry creation."""

    def test_empty_registry(self) -> None:
        """Empty registry has no interfaces or implementations."""
        registry = StaticAnalysisRegistry.empty()

        assert registry.interface_count == 0
        assert registry.implementation_count == 0

    def test_direct_creation(self) -> None:
        """Registry can be created directly with data."""
        interface = InterfaceInfo(
            fqn="myapp.ports.UserRepo",
            module="myapp.ports",
            name="UserRepo",
            methods=frozenset({"get", "save"}),
        )
        impl = ImplementationInfo(
            fqn="myapp.adapters.SqlUserRepo",
            module="myapp.adapters",
            name="SqlUserRepo",
            implements=frozenset({"myapp.ports.UserRepo"}),
        )

        registry = StaticAnalysisRegistry(
            interfaces=MappingProxyType({"myapp.ports.UserRepo": interface}),
            implementations=MappingProxyType({"myapp.adapters.SqlUserRepo": impl}),
            impl_by_interface=MappingProxyType(
                {"myapp.ports.UserRepo": frozenset({"myapp.adapters.SqlUserRepo"})}
            ),
        )

        assert registry.interface_count == 1
        assert registry.implementation_count == 1


class TestStaticAnalysisRegistryFailFirst:
    """Test FAIL-FIRST validation."""

    def test_none_codebase_raises(self) -> None:
        """None codebase raises TypeError."""
        with pytest.raises(TypeError, match="codebase must not be None"):
            StaticAnalysisRegistry.from_codebase(None)  # type: ignore[arg-type]


class TestStaticAnalysisRegistryFromCodebase:
    """Test from_codebase class method."""

    def test_empty_codebase(self) -> None:
        """Empty codebase produces empty registry."""
        codebase = make_codebase()

        registry = StaticAnalysisRegistry.from_codebase(codebase)

        assert registry.interface_count == 0
        assert registry.implementation_count == 0

    def test_protocol_detected(self) -> None:
        """Protocol class is detected as interface."""
        resolved = make_resolved_interface(
            "myapp.ports.UserRepo",
            methods=frozenset({"get", "save"}),
            is_protocol=True,
        )
        module = make_module("myapp.ports", resolved_classes=(resolved,))
        codebase = make_codebase(module)

        registry = StaticAnalysisRegistry.from_codebase(codebase)

        assert registry.is_interface("myapp.ports.UserRepo")
        interface = registry.interfaces["myapp.ports.UserRepo"]
        assert interface.methods == {"get", "save"}

    def test_abc_detected(self) -> None:
        """ABC class is detected as interface."""
        resolved = make_resolved_interface(
            "myapp.base.BaseService",
            methods=frozenset({"process"}),
            is_protocol=False,  # ABC
        )
        module = make_module("myapp.base", resolved_classes=(resolved,))
        codebase = make_codebase(module)

        registry = StaticAnalysisRegistry.from_codebase(codebase)

        assert registry.is_interface("myapp.base.BaseService")

    def test_implementation_detected(self) -> None:
        """Implementation class is detected."""
        interface = make_resolved_interface(
            "myapp.ports.UserRepo",
            is_protocol=True,
        )
        impl = make_resolved_impl(
            "myapp.adapters.SqlUserRepo",
            implements=("myapp.ports.UserRepo",),
        )
        module = make_module(
            "myapp",
            resolved_classes=(interface, impl),
        )
        codebase = make_codebase(module)

        registry = StaticAnalysisRegistry.from_codebase(codebase)

        assert registry.is_implementation("myapp.adapters.SqlUserRepo")
        impl_info = registry.implementations["myapp.adapters.SqlUserRepo"]
        assert "myapp.ports.UserRepo" in impl_info.implements

    def test_impl_by_interface_index(self) -> None:
        """Reverse index from interface to implementations is built."""
        interface = make_resolved_interface("myapp.ports.Repo")
        impl1 = make_resolved_impl("myapp.adapters.SqlRepo", ("myapp.ports.Repo",))
        impl2 = make_resolved_impl("myapp.adapters.MongoRepo", ("myapp.ports.Repo",))
        module = make_module(
            "myapp",
            resolved_classes=(interface, impl1, impl2),
        )
        codebase = make_codebase(module)

        registry = StaticAnalysisRegistry.from_codebase(codebase)

        impls = registry.get_implementations("myapp.ports.Repo")
        assert impls == {"myapp.adapters.SqlRepo", "myapp.adapters.MongoRepo"}

    def test_class_not_implementing_interface_excluded(self) -> None:
        """Regular class not implementing interface is excluded from implementations."""
        interface = make_resolved_interface("myapp.ports.Repo")
        regular = make_resolved_impl(
            "myapp.models.User",
            implements=(),  # No interfaces
        )
        module = make_module(
            "myapp",
            resolved_classes=(interface, regular),
        )
        codebase = make_codebase(module)

        registry = StaticAnalysisRegistry.from_codebase(codebase)

        # User is not an implementation (doesn't implement interfaces)
        assert not registry.is_implementation("myapp.models.User")


class TestStaticAnalysisRegistryQueries:
    """Test registry query methods."""

    def test_is_interface_true(self) -> None:
        """is_interface returns True for registered interface."""
        interface = InterfaceInfo(
            fqn="myapp.ports.Repo",
            module="myapp.ports",
            name="Repo",
            methods=frozenset(),
        )
        registry = StaticAnalysisRegistry(
            interfaces=MappingProxyType({"myapp.ports.Repo": interface}),
            implementations=MappingProxyType({}),
            impl_by_interface=MappingProxyType({}),
        )

        assert registry.is_interface("myapp.ports.Repo") is True

    def test_is_interface_false(self) -> None:
        """is_interface returns False for unknown FQN."""
        registry = StaticAnalysisRegistry.empty()

        assert registry.is_interface("unknown.Class") is False

    def test_is_implementation_true(self) -> None:
        """is_implementation returns True for registered implementation."""
        impl = ImplementationInfo(
            fqn="myapp.adapters.Impl",
            module="myapp.adapters",
            name="Impl",
            implements=frozenset({"myapp.ports.Repo"}),
        )
        registry = StaticAnalysisRegistry(
            interfaces=MappingProxyType({}),
            implementations=MappingProxyType({"myapp.adapters.Impl": impl}),
            impl_by_interface=MappingProxyType({}),
        )

        assert registry.is_implementation("myapp.adapters.Impl") is True

    def test_is_implementation_false(self) -> None:
        """is_implementation returns False for unknown FQN."""
        registry = StaticAnalysisRegistry.empty()

        assert registry.is_implementation("unknown.Class") is False

    def test_get_implementations_existing(self) -> None:
        """get_implementations returns implementations for known interface."""
        registry = StaticAnalysisRegistry(
            interfaces=MappingProxyType({}),
            implementations=MappingProxyType({}),
            impl_by_interface=MappingProxyType(
                {"myapp.ports.Repo": frozenset({"myapp.SqlRepo", "myapp.MongoRepo"})}
            ),
        )

        impls = registry.get_implementations("myapp.ports.Repo")

        assert impls == {"myapp.SqlRepo", "myapp.MongoRepo"}

    def test_get_implementations_unknown(self) -> None:
        """get_implementations returns empty set for unknown interface."""
        registry = StaticAnalysisRegistry.empty()

        impls = registry.get_implementations("unknown.Interface")

        assert impls == frozenset()

    def test_get_implemented_interfaces_existing(self) -> None:
        """get_implemented_interfaces returns interfaces for known impl."""
        impl = ImplementationInfo(
            fqn="myapp.adapters.Impl",
            module="myapp.adapters",
            name="Impl",
            implements=frozenset({"myapp.ports.Repo", "myapp.ports.Cacheable"}),
        )
        registry = StaticAnalysisRegistry(
            interfaces=MappingProxyType({}),
            implementations=MappingProxyType({"myapp.adapters.Impl": impl}),
            impl_by_interface=MappingProxyType({}),
        )

        interfaces = registry.get_implemented_interfaces("myapp.adapters.Impl")

        assert interfaces == {"myapp.ports.Repo", "myapp.ports.Cacheable"}

    def test_get_implemented_interfaces_unknown(self) -> None:
        """get_implemented_interfaces returns empty set for unknown impl."""
        registry = StaticAnalysisRegistry.empty()

        interfaces = registry.get_implemented_interfaces("unknown.Impl")

        assert interfaces == frozenset()
