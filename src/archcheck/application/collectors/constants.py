"""Constants for runtime collectors.

Python 3.14 sys.monitoring tool IDs:
- 0: sys.monitoring.DEBUGGER_ID
- 1: sys.monitoring.COVERAGE_ID
- 2: sys.monitoring.PROFILER_ID
- 5: sys.monitoring.OPTIMIZER_ID
- 3, 4: Available for user tools

We use ID 3 for archcheck.
"""

from typing import Final

# sys.monitoring tool ID for archcheck
# IDs 3 and 4 are available for user tools
ARCHCHECK_TOOL_ID: Final = 3

# Tool name registered with sys.monitoring
ARCHCHECK_TOOL_NAME: Final = "archcheck"
