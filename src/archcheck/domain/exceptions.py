"""Domain exceptions: all public errors of archcheck.

Hexagonal architecture: all exceptions visible to users defined in domain.
Infrastructure/Application use these, not define their own public exceptions.
"""


class ArchCheckError(Exception):
    """Base for all archcheck error exceptions.

    Allows: except ArchCheckError to catch all library errors.
    """


# N818: Signals are NOT errors — no "Error" suffix per PEP 8.
# Same pattern as stdlib: StopIteration, GeneratorExit, SystemExit.
class ArchCheckSignal(Exception):  # noqa: N818
    """Base for all archcheck signal exceptions (flow control, not errors).

    Signals are NOT errors — they control execution flow.
    Like StopIteration, GeneratorExit.

    Allows: except ArchCheckSignal to catch all library signals.
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


class ParseError(ArchCheckError, SyntaxError):
    """Failed to parse Python source file.

    FAIL-FIRST: invalid syntax raises immediately.
    Inherits SyntaxError for semantic correctness.

    Attributes:
        path: Path to file that failed.
        reason: Error description.
    """

    def __init__(self, *, path: str, reason: str) -> None:
        """Initialize with file path and error reason."""
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


class StopTracking(ArchCheckSignal):
    """Signal to stop tracking gracefully.

    Raised from callback to request stop. NOT an error — flow control.
    SafeCallback captures this and sets _stop_requested flag.
    """


class CallbackError(ArchCheckError):
    """Exception from callback during tracking.

    Wraps the original exception. Raised by check_pending_error().
    Preserves original traceback via __cause__.

    Attributes:
        original: Original exception from callback.
    """

    def __init__(self, original: BaseException) -> None:
        """Initialize with original exception."""
        self.original = original
        super().__init__(f"Callback raised: {type(original).__name__}: {original}")
        self.__cause__ = original


class StopFromCallbackError(ArchCheckError, RuntimeError):
    """Cannot call stop() from within callback.

    Detected by barrier — would deadlock.
    """

    def __init__(self) -> None:
        """Initialize with fixed message."""
        super().__init__("Cannot call stop() from within tracking callback")


class InvalidHandlerError(ArchCheckError, TypeError):
    """Handler must be callable.

    Raised when SafeCallback receives non-callable handler.
    Inherits TypeError for semantic correctness.

    Attributes:
        got: Actual type received.
    """

    def __init__(self, got: type) -> None:
        """Initialize with actual type."""
        self.got = got
        super().__init__(f"handler must be callable, got {got.__name__}")


class InvalidCountError(ArchCheckError, ValueError):
    """Count must be >= 1.

    Raised when CallEdge has invalid count.

    Attributes:
        count: Invalid count value.
    """

    def __init__(self, count: int) -> None:
        """Initialize with invalid count."""
        self.count = count
        super().__init__(f"count must be >= 1, got {count}")


class ObjectIdMismatchError(ArchCheckError, ValueError):
    """Object ID mismatch in lifecycle.

    Raised when destroyed event has different obj_id than lifecycle.

    Attributes:
        lifecycle_id: Expected obj_id from lifecycle.
        destroyed_id: Actual obj_id from destroyed event.
    """

    def __init__(self, lifecycle_id: int, destroyed_id: int) -> None:
        """Initialize with mismatched IDs."""
        self.lifecycle_id = lifecycle_id
        self.destroyed_id = destroyed_id
        super().__init__(f"obj_id mismatch: lifecycle={lifecycle_id}, destroyed={destroyed_id}")


class InvalidImportLevelError(ArchCheckError, ValueError):
    """Invalid import level.

    Raised when import level violates constraints.

    Attributes:
        level: Invalid level value.
        reason: Why level is invalid.
    """

    def __init__(self, level: int, reason: str) -> None:
        """Initialize with level and reason."""
        self.level = level
        self.reason = reason
        super().__init__(f"{reason}, got level={level}")


class ModuleNameMismatchError(ArchCheckError, ValueError):
    """Module name does not match key.

    Raised when Codebase module dict has key != module.name.

    Attributes:
        key: Dict key.
        name: Actual module name.
    """

    def __init__(self, key: str, name: str) -> None:
        """Initialize with key and name."""
        self.key = key
        self.name = name
        super().__init__(f"module name {name!r} does not match key {key!r}")


class DuplicateCreateError(ArchCheckError, ValueError):
    """Duplicate CREATE event without DESTROY.

    Raised when second CREATE for same obj_id without intervening DESTROY.

    Attributes:
        obj_id: Duplicated object ID.
    """

    def __init__(self, obj_id: int) -> None:
        """Initialize with obj_id."""
        self.obj_id = obj_id
        super().__init__(f"Duplicate CREATE for obj_id={obj_id} without DESTROY")


class ImportLevelExceedsDepthError(ArchCheckError, ValueError):
    """Relative import level exceeds package depth.

    Raised when trying to import beyond package root.

    Attributes:
        level: Import level requested.
        depth: Package depth available.
    """

    def __init__(self, level: int, depth: int) -> None:
        """Initialize with level and depth."""
        self.level = level
        self.depth = depth
        super().__init__(f"relative import level {level} exceeds package depth {depth}")


class MissingEdgeSourceError(ArchCheckError, ValueError):
    """MergedCallEdge requires at least one source.

    Raised when neither static nor runtime edge present.
    """

    def __init__(self) -> None:
        """Initialize with fixed message."""
        super().__init__("at least one of static or runtime must be present")
