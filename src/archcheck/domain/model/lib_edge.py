"""Library edge value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.call_instance import CallInstance
    from archcheck.domain.model.lib_call_site import LibCallSite
    from archcheck.domain.model.location import Location


@dataclass(frozen=True, slots=True)
class LibEdge:
    """Edge from application function to library function.

    Represents calls from application code to external library code.
    Used for tracking external dependencies and their usage patterns.

    Attributes:
        caller_fqn: Fully qualified name of calling app function
        lib_target: Library function being called
        calls: All call instances for this edge
    """

    caller_fqn: str
    lib_target: LibCallSite
    calls: tuple[CallInstance, ...]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.caller_fqn:
            raise ValueError("caller_fqn must not be empty")
        if self.lib_target is None:
            raise TypeError("lib_target must not be None")
        if not self.calls:
            raise ValueError("calls must not be empty")

    @property
    def total_count(self) -> int:
        """Total runtime call count across all instances."""
        return sum(call.count for call in self.calls)

    @property
    def first_location(self) -> Location:
        """Location of first call instance."""
        return self.calls[0].location

    @property
    def lib_fqn(self) -> str:
        """FQN of library target."""
        return self.lib_target.fqn
