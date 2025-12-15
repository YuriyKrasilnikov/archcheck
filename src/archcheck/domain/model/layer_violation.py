"""Layer boundary violation type."""

from dataclasses import dataclass

from archcheck.domain.model.call_site import CallSite


@dataclass(frozen=True, slots=True)
class LayerViolation:
    """Layer boundary violation.

    Immutable value object with FAIL-FIRST validation.
    Represents a call from one layer to another that violates
    the allowed_imports configuration.

    Attributes:
        caller: CallSite of the calling function
        callee: CallSite of the called function
        caller_layer: Layer name of the caller
        callee_layer: Layer name of the callee (violated layer)
    """

    caller: CallSite
    callee: CallSite
    caller_layer: str
    callee_layer: str

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.caller_layer:
            raise ValueError("caller_layer must not be empty")
        if not self.callee_layer:
            raise ValueError("callee_layer must not be empty")
        if self.caller_layer == self.callee_layer:
            raise ValueError("caller_layer must differ from callee_layer")

    @property
    def message(self) -> str:
        """Human-readable violation message."""
        return f"Layer violation: {self.caller_layer} → {self.callee_layer} at {self.caller}"

    def __str__(self) -> str:
        """Format as caller → callee (layer violation)."""
        return f"{self.caller} → {self.callee} ({self.caller_layer} → {self.callee_layer})"
