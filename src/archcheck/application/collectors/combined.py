"""Combined sync + async runtime collector.

Implements CollectorProtocol by wrapping CallGraphCollector and AsyncCallGraphCollector.
"""

from __future__ import annotations

from pathlib import Path

from archcheck.application.collectors.async_collector import AsyncCallGraphCollector
from archcheck.application.collectors.call_collector import CallGraphCollector
from archcheck.domain.model.combined_call_graph import CombinedCallGraph


class RuntimeArchCollector:
    """Combined sync + async collector implementing CollectorProtocol.

    Wraps:
    - CallGraphCollector: sys.monitoring for sync function calls
    - AsyncCallGraphCollector: asyncio.capture_call_graph for async tasks

    Lifecycle:
        collector = RuntimeArchCollector(base_dir, known_libs)
        collector.start()
        try:
            # Run tests...
            collector.capture_async_snapshot()  # After async tests
        finally:
            result = collector.stop()
    """

    def __init__(self, base_dir: Path, known_libs: frozenset[str]) -> None:
        """Initialize combined collector.

        Args:
            base_dir: Application root directory
            known_libs: Normalized library names from requirements
        """
        self._sync = CallGraphCollector(base_dir, known_libs)
        self._async = AsyncCallGraphCollector(base_dir)

    def start(self) -> None:
        """Start runtime collection.

        Registers sys.monitoring callbacks for function calls.
        Must be called before any code under test runs.

        Raises:
            RuntimeError: If already started
            ToolIdUnavailableError: If tool ID is in use
        """
        self._sync.start()

    def capture_async_snapshot(self) -> bool:
        """Capture async call graph snapshot.

        Calls asyncio.capture_call_graph() to capture current
        task dependency state. Call after async tests complete.

        Returns:
            True if snapshot captured, False if no graph available
        """
        return self._async.capture_snapshot()

    def stop(self) -> CombinedCallGraph:
        """Stop collection and return results.

        Unregisters callbacks and returns immutable call graph.
        Must be called after all code under test has run.

        Returns:
            Combined sync + async call graph

        Raises:
            RuntimeError: If not started
        """
        return CombinedCallGraph(
            function_calls=self._sync.stop(),
            task_dependencies=self._async.build_graph(),
        )

    @property
    def is_started(self) -> bool:
        """Check if collector is currently running."""
        return self._sync.is_started
