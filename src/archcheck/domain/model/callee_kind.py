"""Callee classification enum for runtime analysis."""

from enum import Enum, auto


class CalleeKind(Enum):
    """Classification of callee in runtime call graph.

    Used to distinguish between different types of code being called:
    - APP: Application code (under base_dir, not tests)
    - TEST: Test code (under tests/ directory)
    - LIB: Known external library
    - OTHER: Unknown/stdlib/other code
    """

    APP = auto()  # Application code
    TEST = auto()  # Test code
    LIB = auto()  # Known external library
    OTHER = auto()  # Unknown/stdlib/other
