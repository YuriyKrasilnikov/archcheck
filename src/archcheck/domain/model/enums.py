"""Domain enumerations."""

from enum import Enum, auto


class Visibility(Enum):
    """Code element visibility by naming convention."""

    PUBLIC = auto()  # no underscore
    PROTECTED = auto()  # _name
    PRIVATE = auto()  # __name


class Severity(Enum):
    """Rule violation severity."""

    ERROR = auto()  # test fails
    WARNING = auto()  # test passes, warning shown
    INFO = auto()  # informational


class RuleCategory(Enum):
    """Architecture rule category.

    Categories are organized by validation domain:
    - Structure: IMPORT, NAMING, INHERITANCE, DECORATOR
    - Quality: PURITY, DI, FAIL_FIRST
    - Architecture: BOUNDARIES, COUPLING, COHESION, ISOLATION
    - Contracts: CONTRACTS, QUALITY
    - Runtime: RUNTIME
    - Extension: CUSTOM
    """

    # Structure validation
    IMPORT = auto()
    NAMING = auto()
    INHERITANCE = auto()
    DECORATOR = auto()

    # Quality validation
    PURITY = auto()
    DI = auto()
    FAIL_FIRST = auto()

    # Architecture validation (Layer 3)
    BOUNDARIES = auto()  # layer boundary violations
    COUPLING = auto()  # cycles, fan-out, instability
    COHESION = auto()  # class width, protocol width
    ISOLATION = auto()  # adapter isolation

    # Contract validation
    CONTRACTS = auto()  # interface contracts
    QUALITY = auto()  # code quality (no print, etc.)

    # Runtime validation (Python 3.14)
    RUNTIME = auto()  # runtime call graph validation

    # User extension
    CUSTOM = auto()
