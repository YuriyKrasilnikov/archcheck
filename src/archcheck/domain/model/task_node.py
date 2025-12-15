"""Task node value object for async call graph analysis."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaskNode:
    """Async task node in call graph.

    Immutable value object with FAIL-FIRST validation.
    Represents an asyncio Task captured by asyncio.capture_call_graph() (Python 3.14).

    Domain type - stdlib-independent. Infrastructure converts FutureCallGraph to this.

    Attributes:
        task_name: Task name (from Task.get_name() or Future id)
        task_id: Unique task identifier (from id(future))
        module: Module where task was created (None if call_stack unavailable)
        function: Function where task was created (None if call_stack unavailable)
        line: Line number where task was created (None if call_stack unavailable)
    """

    task_name: str
    task_id: int
    module: str | None
    function: str | None
    line: int | None

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if not self.task_name:
            raise ValueError("task_name must not be empty")
        if self.task_id < 0:
            raise ValueError(f"task_id must be >= 0, got {self.task_id}")
        # module/function/line can be None if call_stack was unavailable
        if self.line is not None and self.line < 1:
            raise ValueError(f"line must be >= 1 or None, got {self.line}")

    @property
    def fqn(self) -> str:
        """Fully qualified name: module.function or task_name if unavailable."""
        if self.module and self.function:
            return f"{self.module}.{self.function}"
        return self.task_name

    def __str__(self) -> str:
        """Format as task_name (module.function:line) or just task_name."""
        if self.module and self.function and self.line:
            return f"{self.task_name} ({self.module}.{self.function}:{self.line})"
        return self.task_name
