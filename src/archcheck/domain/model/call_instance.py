"""Call instance value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.call_type import CallType
    from archcheck.domain.model.location import Location


@dataclass(frozen=True, slots=True)
class CallInstance:
    """Single call instance with location and runtime count.

    Represents one specific call from caller to callee at a particular
    source location. Multiple CallInstances may exist for the same
    (caller, callee) pair if the call appears on different lines.

    Attributes:
        location: Source location where call occurs (file:line:column)
        call_type: How the call is made (FUNCTION/METHOD/DECORATOR/etc.)
        count: Number of times this call was executed at runtime (>= 1)
    """

    location: Location
    call_type: CallType
    count: int

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if self.location is None:
            raise TypeError("location must not be None")
        if self.call_type is None:
            raise TypeError("call_type must not be None")
        if self.count < 1:
            raise ValueError(f"count must be >= 1, got {self.count}")
