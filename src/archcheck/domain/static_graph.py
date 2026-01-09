"""Domain layer: static call graph from AST analysis.

Immutable value objects representing call relationships found in source code.
Data Completeness: unresolved calls tracked, not dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.events import Location


class CallType(Enum):
    """Type of function call in AST.

    DIRECT:      foo()
    METHOD:      self.foo()
    SUPER:       super().foo()
    DECORATOR:   @foo
    CONSTRUCTOR: Foo()
    """

    DIRECT = "DIRECT"
    METHOD = "METHOD"
    SUPER = "SUPER"
    DECORATOR = "DECORATOR"
    CONSTRUCTOR = "CONSTRUCTOR"


@dataclass(frozen=True, slots=True)
class StaticCallEdge:
    """Edge in static call graph: caller → callee from AST.

    caller_fqn and callee_fqn are fully qualified names.
    location is call site in source.
    """

    caller_fqn: str
    callee_fqn: str
    location: Location
    call_type: CallType


@dataclass(frozen=True, slots=True)
class UnresolvedCall:
    """Call that couldn't be resolved to FQN.

    Data Completeness: track what we couldn't resolve and why.

    Reasons: "import not found", "dynamic", "builtin", etc.
    """

    caller_fqn: str
    callee_name: str
    location: Location
    reason: str


@dataclass(frozen=True, slots=True)
class StaticCallGraph:
    """Static call graph from AST analysis.

    edges: resolved calls with FQN
    unresolved: calls we couldn't resolve (Data Completeness)
    """

    edges: tuple[StaticCallEdge, ...]
    unresolved: tuple[UnresolvedCall, ...]

    @classmethod
    def empty(cls) -> StaticCallGraph:
        """Create empty graph for tests or empty merge."""
        return cls(edges=(), unresolved=())
