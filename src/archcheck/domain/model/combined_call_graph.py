"""Combined call graph aggregating sync and async analysis."""

from dataclasses import dataclass

from archcheck.domain.model.async_call_graph import AsyncCallGraph
from archcheck.domain.model.runtime_call_graph import FrozenRuntimeCallGraph


@dataclass(frozen=True, slots=True)
class CombinedCallGraph:
    """Combined sync + async call graph.

    Immutable aggregate of both sync (sys.monitoring) and
    async (asyncio.capture_call_graph) analysis results.

    Attributes:
        function_calls: Sync function call graph (from sys.monitoring)
        task_dependencies: Async task dependency graph
    """

    function_calls: FrozenRuntimeCallGraph
    task_dependencies: AsyncCallGraph

    @property
    def total_edge_count(self) -> int:
        """Total edges across sync and async graphs."""
        return (
            self.function_calls.edge_count
            + self.function_calls.lib_edge_count
            + self.task_dependencies.edge_count
        )

    @property
    def has_async_data(self) -> bool:
        """Check if async data was collected."""
        return self.task_dependencies.task_count > 0
