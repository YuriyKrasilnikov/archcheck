"""Static analysis registry for interfaces and implementations."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from archcheck.domain.model.implementation_info import ImplementationInfo
from archcheck.domain.model.interface_info import InterfaceInfo

if TYPE_CHECKING:
    from collections.abc import Mapping

    from archcheck.domain.model.codebase import Codebase


@dataclass(frozen=True, slots=True)
class StaticAnalysisRegistry:
    """Registry of interfaces and implementations from static analysis.

    Immutable aggregate containing:
    - All Protocol/ABC interfaces found in codebase
    - All implementation classes and which interfaces they implement
    - Index from interface to its implementations

    Used by DIAwareValidator to understand DI patterns.

    Attributes:
        interfaces: Map from FQN to InterfaceInfo
        implementations: Map from FQN to ImplementationInfo
        impl_by_interface: Map from interface FQN to implementation FQNs
    """

    interfaces: Mapping[str, InterfaceInfo]
    implementations: Mapping[str, ImplementationInfo]
    impl_by_interface: Mapping[str, frozenset[str]]

    def is_interface(self, fqn: str) -> bool:
        """Check if FQN is a known interface.

        Args:
            fqn: Fully qualified class name

        Returns:
            True if FQN is in interfaces
        """
        return fqn in self.interfaces

    def is_implementation(self, fqn: str) -> bool:
        """Check if FQN is a known implementation.

        Args:
            fqn: Fully qualified class name

        Returns:
            True if FQN is in implementations
        """
        return fqn in self.implementations

    def get_implementations(self, interface_fqn: str) -> frozenset[str]:
        """Get all implementations of an interface.

        Args:
            interface_fqn: Interface FQN

        Returns:
            Set of implementation FQNs (empty if interface not found)
        """
        return self.impl_by_interface.get(interface_fqn, frozenset())

    def get_implemented_interfaces(self, impl_fqn: str) -> frozenset[str]:
        """Get all interfaces implemented by a class.

        Args:
            impl_fqn: Implementation class FQN

        Returns:
            Set of interface FQNs (empty if not an implementation)
        """
        impl = self.implementations.get(impl_fqn)
        if impl is None:
            return frozenset()
        return impl.implements

    @property
    def interface_count(self) -> int:
        """Number of registered interfaces."""
        return len(self.interfaces)

    @property
    def implementation_count(self) -> int:
        """Number of registered implementations."""
        return len(self.implementations)

    @classmethod
    def empty(cls) -> StaticAnalysisRegistry:
        """Create empty registry."""
        return cls(
            interfaces=MappingProxyType({}),
            implementations=MappingProxyType({}),
            impl_by_interface=MappingProxyType({}),
        )

    @classmethod
    def from_codebase(cls, codebase: Codebase) -> StaticAnalysisRegistry:
        """Build registry from codebase.

        Processes resolved_classes from all modules to identify
        interfaces (Protocol/ABC) and their implementations.

        Args:
            codebase: Parsed codebase with modules

        Returns:
            Registry with interfaces and implementations

        Raises:
            TypeError: If codebase is None (FAIL-FIRST)
        """
        if codebase is None:
            raise TypeError("codebase must not be None")

        interfaces: dict[str, InterfaceInfo] = {}
        implementations: dict[str, ImplementationInfo] = {}

        # First pass: collect all interfaces
        for module in codebase.modules.values():
            for resolved in module.resolved_classes:
                if resolved.is_interface:
                    interfaces[resolved.fqn] = InterfaceInfo(
                        fqn=resolved.fqn,
                        module=resolved.module,
                        name=resolved.name,
                        methods=resolved.interface_methods,
                    )

        # Second pass: collect implementations
        interface_fqns = frozenset(interfaces.keys())
        for module in codebase.modules.values():
            for resolved in module.resolved_classes:
                if not resolved.is_interface:
                    # Find which interfaces this class implements
                    implemented = frozenset(
                        base for base in resolved.resolved_bases if base in interface_fqns
                    )
                    if implemented:
                        implementations[resolved.fqn] = ImplementationInfo(
                            fqn=resolved.fqn,
                            module=resolved.module,
                            name=resolved.name,
                            implements=implemented,
                        )

        # Build reverse index: interface → implementations
        impl_by_interface: dict[str, set[str]] = {}
        for impl_fqn, impl_info in implementations.items():
            for iface_fqn in impl_info.implements:
                if iface_fqn not in impl_by_interface:
                    impl_by_interface[iface_fqn] = set()
                impl_by_interface[iface_fqn].add(impl_fqn)

        # Freeze the index
        frozen_index: dict[str, frozenset[str]] = {
            k: frozenset(v) for k, v in impl_by_interface.items()
        }

        return cls(
            interfaces=MappingProxyType(interfaces),
            implementations=MappingProxyType(implementations),
            impl_by_interface=MappingProxyType(frozen_index),
        )
