"""Implementation info for DI-aware validation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImplementationInfo:
    """Implementation class information.

    Immutable value object with FAIL-FIRST validation.
    Used by DIAwareValidator to understand impl→interface relationships.

    Attributes:
        fqn: Fully qualified name (module.ClassName)
        module: Module where implementation is defined
        name: Implementation class name
        implements: Interface FQNs this class implements
    """

    fqn: str
    module: str
    name: str
    implements: frozenset[str]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.fqn:
            raise ValueError("fqn must not be empty")
        if not self.module:
            raise ValueError("module must not be empty")
        if not self.name:
            raise ValueError("name must not be empty")

        # fqn must be module.name
        expected_fqn = f"{self.module}.{self.name}"
        if self.fqn != expected_fqn:
            raise ValueError(f"fqn must be '{expected_fqn}', got '{self.fqn}'")

    def implements_interface(self, interface_fqn: str) -> bool:
        """Check if this class implements given interface.

        Args:
            interface_fqn: Interface FQN to check

        Returns:
            True if this class implements the interface
        """
        return interface_fqn in self.implements

    def __str__(self) -> str:
        """Format as fqn implements [interfaces]."""
        if self.implements:
            interfaces = ", ".join(sorted(self.implements))
            return f"{self.fqn} implements [{interfaces}]"
        return f"{self.fqn} (no interfaces)"
