"""Collector protocol for runtime data collection.

Collectors gather runtime data using Python 3.14 features:
- sys.monitoring (PEP 669) for function calls
- asyncio.capture_call_graph() for async task dependencies
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from archcheck.domain.model.combined_call_graph import CombinedCallGraph


class CollectorProtocol(Protocol):
    """Contract for runtime collectors.

    Collectors gather call graph data during test execution.
    Must be thread-safe as tests may run in parallel.

    Lifecycle:
    1. start() - Begin collection (register callbacks)
    2. capture_async_snapshot() - Capture async task state (optional)
    3. stop() - End collection and return results

    Example:
        collector = RuntimeArchCollector(base_dir, known_libs)
        collector.start()
        try:
            # Run tests...
            collector.capture_async_snapshot()  # After async tests
        finally:
            result = collector.stop()
    """

    def start(self) -> None:
        """Start runtime collection.

        Registers sys.monitoring callbacks for function calls.
        Must be called before any code under test runs.

        Raises:
            RuntimeError: If already started or tool ID unavailable
        """
        ...

    def capture_async_snapshot(self) -> None:
        """Capture async call graph snapshot.

        Calls asyncio.capture_call_graph() to capture current
        task dependency state. Call after async tests complete.
        """
        ...

    def stop(self) -> CombinedCallGraph:
        """Stop collection and return results.

        Unregisters callbacks and returns immutable call graph.
        Must be called after all code under test has run.

        Returns:
            Combined sync + async call graph

        Raises:
            RuntimeError: If not started
        """
        ...
