"""Runtime call graph collector using sys.monitoring (PEP 669).

Python 3.14 sys.monitoring provides low-overhead function call monitoring.
This collector records function call edges for architecture analysis.

Design decisions:
- Track both PY_START and PY_RETURN for proper call stack maintenance
- Use DISABLE only for OTHER (stdlib) code to reduce overhead
- APP/TEST code fully tracked for accurate edge recording
- LIB code tracked once per code object (DISABLE after first call)
"""

from __future__ import annotations

import contextvars
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING

from archcheck.application.collectors.classifier import classify_callee
from archcheck.application.collectors.constants import (
    ARCHCHECK_TOOL_ID,
    ARCHCHECK_TOOL_NAME,
)
from archcheck.domain.model.call_site import CallSite
from archcheck.domain.model.callee_kind import CalleeKind
from archcheck.domain.model.lib_call_site import LibCallSite
from archcheck.domain.model.runtime_call_graph import (
    FrozenRuntimeCallGraph,
    RuntimeCallGraph,
)

if TYPE_CHECKING:
    pass


class ToolIdUnavailableError(Exception):
    """Raised when sys.monitoring tool ID is already in use."""

    def __init__(self, tool_id: int) -> None:
        self.tool_id = tool_id
        super().__init__(f"sys.monitoring tool ID {tool_id} is already in use")


class CallGraphCollector:
    """Runtime call graph collector using sys.monitoring (PEP 669).

    Thread-safe. Records:
    - edges: caller → callee with count (APP/TEST only)
    - lib_edges: app → lib boundaries
    - called_functions: all called APP/TEST functions

    Uses contextvars for per-task/thread call stack tracking.
    Uses PY_START + PY_RETURN events for proper stack maintenance.

    Lifecycle:
        collector = CallGraphCollector(base_dir, known_libs)
        collector.start()
        # ... run tests ...
        graph = collector.stop()
    """

    def __init__(self, base_dir: Path, known_libs: frozenset[str]) -> None:
        """Initialize collector.

        Args:
            base_dir: Application root directory for classification
            known_libs: Normalized library names from requirements
        """
        if not base_dir.is_dir():
            raise ValueError(f"base_dir must be a directory: {base_dir}")

        self._base_dir = base_dir.resolve()
        self._known_libs = known_libs
        self._graph = RuntimeCallGraph()
        self._started = False

        # Per-task/thread call stack using contextvars
        # Stack contains CallSite for APP/TEST functions only
        self._call_stack: contextvars.ContextVar[list[CallSite]] = contextvars.ContextVar(
            "archcheck_call_stack",
        )

    def start(self) -> None:
        """Register sys.monitoring callbacks and start collection.

        Raises:
            RuntimeError: If already started
            ToolIdUnavailableError: If tool ID is in use
        """
        if self._started:
            raise RuntimeError("collector already started")

        # Register tool ID (raises ValueError if in use)
        try:
            sys.monitoring.use_tool_id(ARCHCHECK_TOOL_ID, ARCHCHECK_TOOL_NAME)
        except ValueError as e:
            raise ToolIdUnavailableError(ARCHCHECK_TOOL_ID) from e

        self._started = True

        # Register callbacks for function entry and return
        sys.monitoring.register_callback(
            ARCHCHECK_TOOL_ID,
            sys.monitoring.events.PY_START,
            self._on_py_start,
        )
        sys.monitoring.register_callback(
            ARCHCHECK_TOOL_ID,
            sys.monitoring.events.PY_RETURN,
            self._on_py_return,
        )

        # Enable events
        sys.monitoring.set_events(
            ARCHCHECK_TOOL_ID,
            sys.monitoring.events.PY_START | sys.monitoring.events.PY_RETURN,
        )

    def stop(self) -> FrozenRuntimeCallGraph:
        """Unregister callbacks and return frozen graph.

        Returns:
            Immutable snapshot of collected call graph

        Raises:
            RuntimeError: If not started
        """
        if not self._started:
            raise RuntimeError("collector not started")

        # Disable events
        sys.monitoring.set_events(ARCHCHECK_TOOL_ID, 0)

        # Unregister callbacks
        sys.monitoring.register_callback(
            ARCHCHECK_TOOL_ID,
            sys.monitoring.events.PY_START,
            None,
        )
        sys.monitoring.register_callback(
            ARCHCHECK_TOOL_ID,
            sys.monitoring.events.PY_RETURN,
            None,
        )

        # Free tool ID
        sys.monitoring.free_tool_id(ARCHCHECK_TOOL_ID)

        self._started = False

        return self._graph.freeze()

    @property
    def is_started(self) -> bool:
        """Check if collector is currently running."""
        return self._started

    def _get_stack(self) -> list[CallSite]:
        """Get call stack for current context, creating if needed."""
        try:
            return self._call_stack.get()
        except LookupError:
            stack: list[CallSite] = []
            self._call_stack.set(stack)
            return stack

    def _on_py_start(self, code: types.CodeType, instruction_offset: int) -> object:
        """Callback for function entry (PY_START event).

        Args:
            code: Code object of called function
            instruction_offset: Bytecode offset (unused)

        Returns:
            sys.monitoring.DISABLE for OTHER/LIB to reduce overhead
            None for APP/TEST to continue tracking
        """
        # Classify callee by filename
        callee_info = classify_callee(
            code.co_filename,
            self._base_dir,
            self._known_libs,
        )

        stack = self._get_stack()

        match callee_info.kind:
            case CalleeKind.APP | CalleeKind.TEST:
                # CalleeInfo validates module is not None for APP/TEST
                module = callee_info.module
                if module is None:
                    raise TypeError("CalleeInfo invariant violated: APP/TEST requires module")

                # Create CallSite for this function
                callee = CallSite(
                    module=module,
                    function=code.co_qualname,
                    line=code.co_firstlineno,
                    file=Path(code.co_filename),
                )

                # Record edge if we have a caller on stack
                if stack:
                    caller = stack[-1]
                    self._graph.record_edge(caller, callee)

                # Push onto stack (will be popped on PY_RETURN)
                stack.append(callee)

                # Don't disable - need PY_RETURN to pop
                return None

            case CalleeKind.LIB:
                # CalleeInfo validates lib_name is not None for LIB
                lib_name = callee_info.lib_name
                if lib_name is None:
                    raise TypeError("CalleeInfo invariant violated: LIB requires lib_name")

                # Record lib edge if we have an app caller
                if stack:
                    caller = stack[-1]
                    lib_callee = LibCallSite(
                        lib_name=lib_name,
                        function=code.co_qualname,
                    )
                    self._graph.record_lib_edge(caller, lib_callee)

                # Disable - don't need to track lib internals
                return sys.monitoring.DISABLE

            case CalleeKind.OTHER:
                # Ignore stdlib/unknown - disable for performance
                return sys.monitoring.DISABLE

    def _on_py_return(
        self,
        code: types.CodeType,
        instruction_offset: int,
        retval: object,
    ) -> object:
        """Callback for function return (PY_RETURN event).

        Pops the call stack when APP/TEST function returns.

        Args:
            code: Code object of returning function
            instruction_offset: Bytecode offset (unused)
            retval: Return value (unused)

        Returns:
            None (don't disable - need to track all returns)
        """
        # Classify to check if this is APP/TEST
        callee_info = classify_callee(
            code.co_filename,
            self._base_dir,
            self._known_libs,
        )

        match callee_info.kind:
            case CalleeKind.APP | CalleeKind.TEST:
                stack = self._get_stack()
                if stack:
                    stack.pop()

            case CalleeKind.LIB | CalleeKind.OTHER:
                # These were disabled in PY_START, shouldn't reach here
                pass

        return None
