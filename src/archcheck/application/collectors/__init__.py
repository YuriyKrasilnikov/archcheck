"""Runtime collectors for architecture analysis.

Collectors gather runtime data using Python 3.14 features:
- sys.monitoring (PEP 669) for function calls
- asyncio.capture_call_graph() for async task dependencies
"""

from archcheck.application.collectors.async_collector import AsyncCallGraphCollector
from archcheck.application.collectors.call_collector import (
    CallGraphCollector,
    ToolIdUnavailableError,
)
from archcheck.application.collectors.classifier import classify_callee
from archcheck.application.collectors.combined import RuntimeArchCollector
from archcheck.application.collectors.constants import (
    ARCHCHECK_TOOL_ID,
    ARCHCHECK_TOOL_NAME,
)

__all__ = [
    # Constants
    "ARCHCHECK_TOOL_ID",
    "ARCHCHECK_TOOL_NAME",
    # Classifier
    "classify_callee",
    # Collectors
    "CallGraphCollector",
    "AsyncCallGraphCollector",
    "RuntimeArchCollector",
    # Exceptions
    "ToolIdUnavailableError",
]
