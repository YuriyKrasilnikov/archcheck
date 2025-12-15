"""Stack-based context tracking for AST analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class ContextType(Enum):
    """AST context types for scope tracking."""

    MODULE = auto()
    CLASS = auto()
    FUNCTION = auto()
    TYPE_CHECKING = auto()
    CONDITIONAL = auto()
    LOOP = auto()
    COMPREHENSION = auto()


@dataclass(slots=True)
class ContextFrame:
    """Single context frame on the stack.

    Attributes:
        type: Context type
        name: Optional name (class name, function name)
    """

    type: ContextType
    name: str | None = None


@dataclass(slots=True)
class AnalysisContext:
    """Stack-based context for AST traversal.

    Tracks nested scopes with O(1) queries via cached counters.
    Mutable - push/pop during traversal.

    Attributes:
        _stack: Context stack
        _type_checking_depth: Nesting depth in TYPE_CHECKING blocks
        _function_depth: Nesting depth in functions
        _conditional_depth: Nesting depth in conditionals
        _class_depth: Nesting depth in classes
        _loop_depth: Nesting depth in loops
        _comprehension_depth: Nesting depth in comprehensions
    """

    _stack: list[ContextFrame] = field(default_factory=list)
    _type_checking_depth: int = 0
    _function_depth: int = 0
    _conditional_depth: int = 0
    _class_depth: int = 0
    _loop_depth: int = 0
    _comprehension_depth: int = 0

    def push(self, ctx_type: ContextType, name: str | None = None) -> None:
        """Enter new context. O(1).

        Args:
            ctx_type: Type of context to enter
            name: Optional name for the context (REQUIRED for FUNCTION/CLASS)

        Raises:
            TypeError: If ctx_type is not a ContextType (FAIL-FIRST)
            ValueError: If name is empty string, or missing for FUNCTION/CLASS
        """
        # FAIL-FIRST: ctx_type must be valid ContextType
        if not isinstance(ctx_type, ContextType):
            raise TypeError(f"ctx_type must be ContextType, got {type(ctx_type).__name__}")

        if name is not None and name == "":
            raise ValueError("context name must be non-empty string or None")

        # FAIL-FIRST: FUNCTION and CLASS require name for current_function/current_class
        if ctx_type in (ContextType.FUNCTION, ContextType.CLASS) and name is None:
            raise ValueError(f"{ctx_type.name} context requires name")

        self._stack.append(ContextFrame(ctx_type, name))

        match ctx_type:
            case ContextType.TYPE_CHECKING:
                self._type_checking_depth += 1
            case ContextType.FUNCTION:
                self._function_depth += 1
            case ContextType.CONDITIONAL:
                self._conditional_depth += 1
            case ContextType.CLASS:
                self._class_depth += 1
            case ContextType.LOOP:
                self._loop_depth += 1
            case ContextType.COMPREHENSION:
                self._comprehension_depth += 1
            case ContextType.MODULE:
                pass  # MODULE doesn't increment any counter

    def pop(self) -> ContextFrame:
        """Exit current context. O(1).

        Returns:
            The popped context frame

        Raises:
            IndexError: If stack is empty
        """
        if not self._stack:
            raise IndexError("cannot pop from empty context stack")

        frame = self._stack.pop()

        match frame.type:
            case ContextType.TYPE_CHECKING:
                self._type_checking_depth -= 1
            case ContextType.FUNCTION:
                self._function_depth -= 1
            case ContextType.CONDITIONAL:
                self._conditional_depth -= 1
            case ContextType.CLASS:
                self._class_depth -= 1
            case ContextType.LOOP:
                self._loop_depth -= 1
            case ContextType.COMPREHENSION:
                self._comprehension_depth -= 1
            case ContextType.MODULE:
                pass  # MODULE doesn't decrement any counter

        return frame

    @property
    def in_type_checking(self) -> bool:
        """Check if inside TYPE_CHECKING block. O(1)."""
        return self._type_checking_depth > 0

    @property
    def in_function(self) -> bool:
        """Check if inside function/method. O(1)."""
        return self._function_depth > 0

    @property
    def in_conditional(self) -> bool:
        """Check if inside conditional (if/try). O(1)."""
        return self._conditional_depth > 0

    @property
    def in_class(self) -> bool:
        """Check if inside class. O(1)."""
        return self._class_depth > 0

    @property
    def in_loop(self) -> bool:
        """Check if inside loop (for/while). O(1)."""
        return self._loop_depth > 0

    @property
    def in_comprehension(self) -> bool:
        """Check if inside comprehension. O(1)."""
        return self._comprehension_depth > 0

    @property
    def current_class(self) -> str | None:
        """Find enclosing class name. O(depth)."""
        for frame in reversed(self._stack):
            if frame.type == ContextType.CLASS:
                return frame.name
        return None

    @property
    def current_function(self) -> str | None:
        """Find enclosing function name. O(depth)."""
        for frame in reversed(self._stack):
            if frame.type == ContextType.FUNCTION:
                return frame.name
        return None

    @property
    def depth(self) -> int:
        """Current nesting depth (stack size)."""
        return len(self._stack)

    @property
    def is_empty(self) -> bool:
        """Check if context stack is empty."""
        return len(self._stack) == 0
