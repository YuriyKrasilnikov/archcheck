"""Async call graph for Python 3.14 asyncio.capture_call_graph() analysis."""

from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter

from archcheck.domain.model.task_edge import TaskEdge
from archcheck.domain.model.task_node import TaskNode


@dataclass(frozen=True, slots=True)
class AsyncCallGraph:
    """Async task dependency graph.

    Immutable aggregate of task dependencies captured by
    asyncio.capture_call_graph() (Python 3.14+).

    Domain type - stdlib-independent. Infrastructure converts FutureCallGraph to this.

    Attributes:
        task_edges: All waiter → awaited edges
        all_tasks: All tasks observed
    """

    task_edges: frozenset[TaskEdge]
    all_tasks: frozenset[TaskNode]

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        # All tasks in edges must be in all_tasks
        tasks_in_edges: set[TaskNode] = set()
        for edge in self.task_edges:
            tasks_in_edges.add(edge.waiter)
            tasks_in_edges.add(edge.awaited)

        if not tasks_in_edges <= self.all_tasks:
            missing = tasks_in_edges - self.all_tasks
            raise ValueError(f"edges contain tasks not in all_tasks: {missing}")

    @property
    def edge_count(self) -> int:
        """Number of task dependency edges."""
        return len(self.task_edges)

    @property
    def task_count(self) -> int:
        """Number of unique tasks."""
        return len(self.all_tasks)

    @property
    def has_cycles(self) -> bool:
        """Check for task dependency cycles using graphlib.TopologicalSorter.

        Returns:
            True if cycles exist in task dependencies.
        """
        if not self.task_edges:
            return False

        # Build adjacency dict: waiter -> set of awaited tasks
        adjacency: dict[str, set[str]] = {}
        for edge in self.task_edges:
            waiter_fqn = edge.waiter.fqn
            awaited_fqn = edge.awaited.fqn
            adjacency.setdefault(waiter_fqn, set()).add(awaited_fqn)

        try:
            tuple(TopologicalSorter(adjacency).static_order())
            return False
        except CycleError:
            return True

    def get_awaited_by(self, task: TaskNode) -> frozenset[TaskNode]:
        """Get tasks that this task awaits.

        Args:
            task: Task to query

        Returns:
            Tasks awaited by the given task
        """
        return frozenset(edge.awaited for edge in self.task_edges if edge.waiter == task)

    def get_waiters_of(self, task: TaskNode) -> frozenset[TaskNode]:
        """Get tasks waiting on this task.

        Args:
            task: Task to query

        Returns:
            Tasks waiting for the given task
        """
        return frozenset(edge.waiter for edge in self.task_edges if edge.awaited == task)

    @classmethod
    def empty(cls) -> AsyncCallGraph:
        """Create empty async call graph."""
        return cls(task_edges=frozenset(), all_tasks=frozenset())
