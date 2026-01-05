"""Domain exceptions: all public errors of archcheck.

Hexagonal architecture: all exceptions visible to users defined in domain.
Infrastructure/Application use these, not define their own public exceptions.
"""


class ArchCheckError(Exception):
    """Base for all archcheck exceptions.

    Allows: except ArchCheckError to catch all library errors.
    """


class ConversionError(ArchCheckError, TypeError):
    """C extension returned unexpected type.

    Inherits TypeError for semantic correctness (expected type X, got Y).
    Inherits ArchCheckError for unified exception handling.

    Attributes:
        expected: Description of expected type(s).
        got: Actual type received.
    """

    def __init__(self, *, expected: str, got: type) -> None:
        """Initialize with expected type description and actual type."""
        self.expected = expected
        self.got = got
        super().__init__(f"{expected}, got {got.__name__}")


class AlreadyActiveError(ArchCheckError, RuntimeError):
    """Tracking already active, cannot start again.

    Inherits RuntimeError for semantic correctness (invalid state).
    """

    def __init__(self) -> None:
        """Initialize with fixed message."""
        super().__init__("Tracking already active")


class NotExitedError(ArchCheckError, RuntimeError):
    """Context not exited, result not available.

    Raised when accessing TrackingHandle.result before context exit.
    """

    def __init__(self) -> None:
        """Initialize with fixed message."""
        super().__init__("Context not exited, result not available")
