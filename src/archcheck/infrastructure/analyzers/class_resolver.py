"""Class resolver for interface/implementation detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from archcheck.domain.model.resolved_class import ResolvedClass

if TYPE_CHECKING:
    from archcheck.domain.model.class_ import Class
    from archcheck.domain.model.symbol_table import SymbolTable


# Known Protocol/ABC markers for interface detection
_PROTOCOL_MARKERS = frozenset(
    {
        "Protocol",
        "typing.Protocol",
        "typing_extensions.Protocol",
    }
)

_ABC_MARKERS = frozenset(
    {
        "ABC",
        "abc.ABC",
        "ABCMeta",
        "abc.ABCMeta",
    }
)


class ClassResolver:
    """Resolves class bases and detects Protocol/ABC interfaces.

    Stateless - no state between resolve() calls.
    """

    def resolve(
        self,
        classes: tuple[Class, ...],
        symbol_table: SymbolTable | None = None,
    ) -> tuple[ResolvedClass, ...]:
        """Resolve classes to detect interfaces and implementations.

        Args:
            classes: Raw Class objects from AST
            symbol_table: Symbol table for name resolution

        Returns:
            Tuple of ResolvedClass with resolved bases and interface detection
        """
        return tuple(self._resolve_class(cls, symbol_table) for cls in classes)

    def _resolve_class(
        self,
        cls: Class,
        symbol_table: SymbolTable | None,
    ) -> ResolvedClass:
        """Resolve single class.

        Args:
            cls: Raw Class from AST
            symbol_table: Symbol table for resolution

        Returns:
            ResolvedClass with resolved information
        """
        # Resolve bases
        resolved_bases = self._resolve_bases(cls.bases, symbol_table)

        # Detect Protocol
        is_protocol = self._is_protocol(resolved_bases)

        # Detect ABC
        is_abc = self._is_abc(resolved_bases)

        # Extract interface methods (abstract methods)
        interface_methods = self._extract_interface_methods(cls)

        return ResolvedClass(
            fqn=cls.qualified_name,
            raw_bases=cls.bases,
            resolved_bases=resolved_bases,
            is_protocol=is_protocol,
            is_abc=is_abc,
            interface_methods=interface_methods,
        )

    def _resolve_bases(
        self,
        bases: tuple[str, ...],
        symbol_table: SymbolTable | None,
    ) -> tuple[str, ...]:
        """Resolve base class names to FQNs.

        Args:
            bases: Raw base class names from AST
            symbol_table: Symbol table for resolution

        Returns:
            Tuple of resolved FQNs (or original if unresolvable)
        """
        if symbol_table is None:
            return bases

        resolved: list[str] = []
        for base in bases:
            # Try to resolve through symbol table
            resolved_fqn = symbol_table.resolve(base)
            if resolved_fqn is not None:
                resolved.append(resolved_fqn)
            else:
                # Keep original if cannot resolve
                resolved.append(base)

        return tuple(resolved)

    def _is_protocol(self, resolved_bases: tuple[str, ...]) -> bool:
        """Check if class inherits from Protocol.

        Args:
            resolved_bases: Resolved base class FQNs

        Returns:
            True if any base is Protocol
        """
        for base in resolved_bases:
            if base in _PROTOCOL_MARKERS:
                return True
            # Check suffix match (e.g., "mymodule.Protocol" might be Protocol)
            if base.endswith(".Protocol"):
                return True
        return False

    def _is_abc(self, resolved_bases: tuple[str, ...]) -> bool:
        """Check if class inherits from ABC/ABCMeta.

        Args:
            resolved_bases: Resolved base class FQNs

        Returns:
            True if any base is ABC/ABCMeta
        """
        for base in resolved_bases:
            if base in _ABC_MARKERS:
                return True
            # Check suffix match
            if base.endswith(".ABC") or base.endswith(".ABCMeta"):
                return True
        return False

    def _extract_interface_methods(self, cls: Class) -> frozenset[str]:
        """Extract abstract method names from class.

        Args:
            cls: Class object

        Returns:
            Set of abstract method names
        """
        return frozenset(method.name for method in cls.methods if method.is_abstract)
