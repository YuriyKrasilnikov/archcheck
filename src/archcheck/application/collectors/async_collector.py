"""Async call graph collector using asyncio.capture_call_graph() (Python 3.14).

Python 3.14 asyncio.capture_call_graph() captures task dependency tree.
This collector converts stdlib FutureCallGraph to domain AsyncCallGraph.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from archcheck.domain.model.async_call_graph import AsyncCallGraph
from archcheck.domain.model.task_edge import TaskEdge
from archcheck.domain.model.task_node import TaskNode

if TYPE_CHECKING:
    from asyncio import FutureCallGraph


class AsyncCallGraphCollector:
    """Async call graph collector using asyncio.capture_call_graph() (Python 3.14).

    Captures task dependency snapshots during test execution.
    Converts stdlib FutureCallGraph tree to domain AsyncCallGraph.

    Domain types (TaskNode, TaskEdge, AsyncCallGraph) are stdlib-independent.

    Lifecycle:
        collector = AsyncCallGraphCollector(app_dir)
        # ... run async tests ...
        collector.capture_snapshot()  # Call periodically
        graph = collector.build_graph()
    """

    def __init__(self, app_dir: Path) -> None:
        """Initialize collector.

        Args:
            app_dir: Application directory (for future filtering)
        """
        self._app_dir = app_dir.resolve()
        self._snapshots: list[FutureCallGraph] = []

    def capture_snapshot(self) -> bool:
        """Capture current async call graph snapshot.

        Call periodically during test execution to capture task dependencies.
        Each snapshot is a tree rooted at current/specified task.

        Returns:
            True if snapshot was captured, False if no graph available
        """
        graph = asyncio.capture_call_graph()
        if graph is not None:
            self._snapshots.append(graph)
            return True
        return False

    def build_graph(self) -> AsyncCallGraph:
        """Build AsyncCallGraph from all snapshots.

        Converts stdlib FutureCallGraph trees to domain types.
        Deduplicates tasks across snapshots.

        Returns:
            Domain AsyncCallGraph with all captured task dependencies
        """
        all_tasks: set[TaskNode] = set()
        task_edges: set[TaskEdge] = set()

        for snapshot in self._snapshots:
            self._traverse_tree(snapshot, all_tasks, task_edges)

        return AsyncCallGraph(
            task_edges=frozenset(task_edges),
            all_tasks=frozenset(all_tasks),
        )

    def clear(self) -> None:
        """Clear all captured snapshots."""
        self._snapshots.clear()

    @property
    def snapshot_count(self) -> int:
        """Number of captured snapshots."""
        return len(self._snapshots)

    def _traverse_tree(
        self,
        node: FutureCallGraph,
        all_tasks: set[TaskNode],
        task_edges: set[TaskEdge],
    ) -> TaskNode:
        """Recursively convert FutureCallGraph tree to domain types.

        FutureCallGraph is a tree where:
        - node.future: The task/future at this node
        - node.awaited_by: Tasks waiting on this node (recursive tree)

        We convert to flat edges: waiter → awaited

        Args:
            node: Current FutureCallGraph node
            all_tasks: Accumulator for all TaskNodes
            task_edges: Accumulator for all TaskEdges

        Returns:
            TaskNode for this FutureCallGraph node
        """
        task_node = self._convert_to_task_node(node)
        all_tasks.add(task_node)

        # awaited_by contains tasks that are waiting on this task
        for awaiter_graph in node.awaited_by:
            awaiter_node = self._traverse_tree(awaiter_graph, all_tasks, task_edges)
            # awaiter waits on (awaits) task_node
            # Direction: waiter → awaited
            task_edges.add(TaskEdge(waiter=awaiter_node, awaited=task_node))

        return task_node

    def _convert_to_task_node(self, graph: FutureCallGraph) -> TaskNode:
        """Convert single FutureCallGraph to domain TaskNode.

        Args:
            graph: FutureCallGraph to convert

        Returns:
            Domain TaskNode
        """
        future = graph.future

        # Get task name
        if isinstance(future, asyncio.Task):
            task_name = future.get_name()
        else:
            task_name = f"Future@{id(future)}"

        task_id = id(future)

        # Extract module/function/line from call_stack if available
        module: str | None = None
        function: str | None = None
        line: int | None = None

        if graph.call_stack:
            frame_entry = graph.call_stack[0]  # topmost frame
            frame = frame_entry.frame
            module = frame.f_globals.get("__name__")
            function = frame.f_code.co_qualname
            line = frame.f_lineno

        return TaskNode(
            task_name=task_name,
            task_id=task_id,
            module=module,
            function=function,
            line=line,
        )
