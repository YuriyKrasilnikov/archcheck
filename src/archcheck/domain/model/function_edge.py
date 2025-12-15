"""Function edge value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from archcheck.domain.model.edge_nature import EdgeNature

if TYPE_CHECKING:
    from archcheck.domain.model.call_instance import CallInstance
    from archcheck.domain.model.location import Location


@dataclass(frozen=True, slots=True)
class FunctionEdge:
    """Edge between two functions in call graph.

    Represents the relationship between caller and callee functions,
    aggregating all call instances (different source locations where
    caller calls callee).

    Key property: is_boundary_relevant determines if this edge should
    be checked by boundary validators. Only DIRECT edges are checked.

    Attributes:
        caller_fqn: Fully qualified name of calling function
        callee_fqn: Fully qualified name of called function
        nature: Semantic nature of the edge (DIRECT/PARAMETRIC/INHERITED/FRAMEWORK)
        calls: All call instances for this edge (different locations/counts)
    """

    caller_fqn: str
    callee_fqn: str
    nature: EdgeNature
    calls: tuple[CallInstance, ...]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.caller_fqn:
            raise ValueError("caller_fqn must not be empty")
        if not self.callee_fqn:
            raise ValueError("callee_fqn must not be empty")
        if self.caller_fqn == self.callee_fqn:
            raise ValueError("caller_fqn must differ from callee_fqn (no self-loops)")
        if self.nature is None:
            raise TypeError("nature must not be None")
        if not self.calls:
            raise ValueError("calls must not be empty (edge without calls cannot exist)")

    @property
    def total_count(self) -> int:
        """Total runtime call count across all instances."""
        return sum(call.count for call in self.calls)

    @property
    def is_boundary_relevant(self) -> bool:
        """Should boundary validators check this edge?

        Only DIRECT edges represent actual code dependencies.
        PARAMETRIC, INHERITED, and FRAMEWORK edges are not violations.
        """
        return self.nature == EdgeNature.DIRECT

    @property
    def first_location(self) -> Location:
        """Location of first call instance (for Violation reporting)."""
        return self.calls[0].location

    @property
    def fqn_pair(self) -> tuple[str, str]:
        """(caller_fqn, callee_fqn) tuple for indexing."""
        return (self.caller_fqn, self.callee_fqn)
