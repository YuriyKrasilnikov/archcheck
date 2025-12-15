"""Task edge value object for async call graph analysis."""

from dataclasses import dataclass

from archcheck.domain.model.task_node import TaskNode


@dataclass(frozen=True, slots=True)
class TaskEdge:
    """Async task dependency edge.

    Immutable value object with FAIL-FIRST validation.
    Represents waiter → awaited relationship between tasks.

    Attributes:
        waiter: Task that is waiting (caller)
        awaited: Task being awaited (callee)
    """

    waiter: TaskNode
    awaited: TaskNode

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if self.waiter == self.awaited:
            raise ValueError("task cannot await itself")

    def __str__(self) -> str:
        """Format as waiter → awaited."""
        return f"{self.waiter.task_name} → {self.awaited.task_name}"
