"""Edge nature enum for call graph analysis."""

from enum import Enum, auto


class EdgeNature(Enum):
    """Semantic nature of edge between two functions.

    Classifies HOW caller relates to callee:

    DIRECT:
        Caller imports callee's module and calls callee directly.
        This is the standard dependency that boundary validation checks.
        Example: `from myapp.domain import User; User()`

    PARAMETRIC:
        Caller calls callee through a parameter (HOF, callback, DI).
        NOT a boundary violation because caller doesn't know concrete callee.
        Example: `def process(items, transform): return [transform(x) for x in items]`

    INHERITED:
        Caller calls callee through super().
        Inheritance is explicit, not a hidden dependency.
        Example: `super().__init__()`

    FRAMEWORK:
        Framework code calls application code (event handlers, test runners).
        NOT a boundary violation because framework initiates the call.
        Example: pytest calling test_* functions
    """

    DIRECT = auto()
    PARAMETRIC = auto()
    INHERITED = auto()
    FRAMEWORK = auto()
