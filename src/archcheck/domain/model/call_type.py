"""Call type enum for static analysis."""

from enum import Enum, auto


class CallType(Enum):
    """Type of function call in static analysis.

    Classifies how a function is called in AST analysis.
    """

    FUNCTION = auto()  # Regular function call: func()
    METHOD = auto()  # Method call: obj.method()
    DECORATOR = auto()  # Decorator application: @decorator
    CONSTRUCTOR = auto()  # Class instantiation: MyClass()
    SUPER = auto()  # Super call: super().method()
