"""Interface info for DI-aware validation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InterfaceInfo:
    """Interface (Protocol/ABC) information.

    Immutable value object with FAIL-FIRST validation.
    Used by DIAwareValidator to understand interface contracts.

    Attributes:
        fqn: Fully qualified name (module.ClassName)
        module: Module where interface is defined
        name: Interface class name
        methods: Method names defined in interface
    """

    fqn: str
    module: str
    name: str
    methods: frozenset[str]

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

    def __str__(self) -> str:
        """Format as fqn (N methods)."""
        return f"{self.fqn} ({len(self.methods)} methods)"
