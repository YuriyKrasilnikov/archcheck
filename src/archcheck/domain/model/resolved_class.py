"""Resolved class information for DI-aware validation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolvedClass:
    """Class with resolved base information.

    Immutable value object with FAIL-FIRST validation.
    Contains both raw AST data and resolved information.

    Used to determine:
    - Is this class a Protocol/ABC (interface)?
    - What interfaces does this class implement?
    - What methods constitute the interface contract?

    Attributes:
        fqn: Fully qualified class name (module.ClassName)
        raw_bases: Base class names as they appear in source
        resolved_bases: Base class FQNs (resolved where possible)
        is_protocol: True if class inherits from Protocol
        is_abc: True if class inherits from ABC/ABCMeta
        interface_methods: Abstract method names (for interfaces)
    """

    fqn: str
    raw_bases: tuple[str, ...]
    resolved_bases: tuple[str, ...]
    is_protocol: bool
    is_abc: bool
    interface_methods: frozenset[str]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.fqn:
            raise ValueError("fqn must not be empty")

        if len(self.raw_bases) != len(self.resolved_bases):
            raise ValueError(
                f"raw_bases and resolved_bases must have same length: "
                f"{len(self.raw_bases)} != {len(self.resolved_bases)}"
            )

    @property
    def is_interface(self) -> bool:
        """Check if class is an interface (Protocol or ABC)."""
        return self.is_protocol or self.is_abc

    @property
    def module(self) -> str:
        """Extract module from FQN."""
        parts = self.fqn.rsplit(".", 1)
        if len(parts) == 2:
            return parts[0]
        return ""

    @property
    def name(self) -> str:
        """Extract class name from FQN."""
        return self.fqn.rsplit(".", 1)[-1]

    @property
    def has_abstract_methods(self) -> bool:
        """Check if class has abstract methods."""
        return len(self.interface_methods) > 0

    def implements(self, interface_fqn: str) -> bool:
        """Check if this class implements given interface.

        Args:
            interface_fqn: FQN of interface to check

        Returns:
            True if interface_fqn is in resolved_bases
        """
        return interface_fqn in self.resolved_bases

    def __str__(self) -> str:
        """Format as fqn (interface/impl) [N bases]."""
        kind = "interface" if self.is_interface else "impl"
        return f"{self.fqn} ({kind}) [{len(self.raw_bases)} bases]"
