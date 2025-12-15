"""Application layer for architecture analysis.

Phase 3 components:
- discovery: Layer/module/library discovery
- collectors: Runtime call graph collection (sys.monitoring, asyncio)
- validators: Architecture validation (cycles, boundaries)
- reporters: Output formatting (PlainText, JSON)
- services: Main facade (ArchChecker)
"""

from archcheck.application.collectors import (
    ARCHCHECK_TOOL_ID,
    AsyncCallGraphCollector,
    CallGraphCollector,
    RuntimeArchCollector,
    ToolIdUnavailableError,
    classify_callee,
)
from archcheck.application.discovery import (
    discover_layers,
    discover_modules,
    load_known_libs,
)
from archcheck.application.reporters import (
    BaseReporter,
    JSONReporter,
    PlainTextReporter,
)
from archcheck.application.services import ArchChecker
from archcheck.application.validators import (
    BaseValidator,
    BoundaryValidator,
    CycleValidator,
    default_validators,
    validators_from_config,
)

__all__ = [
    # Discovery
    "discover_layers",
    "discover_modules",
    "load_known_libs",
    # Collectors
    "ARCHCHECK_TOOL_ID",
    "classify_callee",
    "CallGraphCollector",
    "AsyncCallGraphCollector",
    "RuntimeArchCollector",
    "ToolIdUnavailableError",
    # Validators
    "BaseValidator",
    "CycleValidator",
    "BoundaryValidator",
    "default_validators",
    "validators_from_config",
    # Reporters
    "BaseReporter",
    "PlainTextReporter",
    "JSONReporter",
    # Services
    "ArchChecker",
]
