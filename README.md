# archcheck

[![Tests](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/test.yml/badge.svg)](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/test.yml)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Runtime data flow tracking for Python 3.14. C extension with PyRefTracer API.

## Requirements

- Python 3.14+
- GCC 15+ (C23 standard)
- uv (package manager)

## Installation

```bash
uv add archcheck
```

## Quick Start

```python
from archcheck.application.services.tracker import TrackerService
from archcheck.application.services.analyzer import AnalyzerService
from archcheck.application.reporters.console import ConsoleReporter
from archcheck.domain.graphs import FilterConfig

# Track execution
tracker = TrackerService()
result, tr = tracker.track(my_function)

# Analyze
analyzer = AnalyzerService()
config = FilterConfig(include_paths=("src/*",), exclude_paths=("*test*",))
analysis = analyzer.analyze(tr, config)

# Results
print(f"Call edges: {len(analysis.call_graph.edges)}")
print(f"Objects tracked: {len(analysis.object_flow.objects)}")

# Report
reporter = ConsoleReporter()
print(reporter.report(tr))
```

## Architecture

```
src/archcheck/
├── domain/
│   ├── events.py          # Location, CallEvent, ReturnEvent, CreateEvent, DestroyEvent
│   ├── graphs.py          # CallEdge, CallGraph, ObjectFlow, FilterConfig, AnalysisResult
│   └── exceptions.py      # ArchCheckError, ConversionError
├── infrastructure/
│   ├── tracking.py        # C binding → domain objects
│   └── filters/           # Filter functions (pure, stateless)
│       ├── event_type.py  # include_types(), exclude_types()
│       ├── path.py        # include_paths(), exclude_paths()
│       └── composite.py   # all_of(), any_of(), negate()
└── application/
    ├── services/
    │   ├── tracker.py     # TrackerService
    │   └── analyzer.py    # AnalyzerService
    └── reporters/
        ├── console.py     # ConsoleReporter (rich)
        ├── json.py        # JsonReporter
        └── strategies.py  # GroupStrategy (ByType, ByFile, ByFunc)

c/
├── _tracking.c            # Main C module
└── tracking/
    ├── constants.h        # constexpr sizes
    ├── types.h            # structs + static_assert
    ├── memory.h           # copy/free helpers
    ├── errors.h           # error capture
    ├── events.h           # fill_*_event()
    └── output.h           # serialize_event()
```

## Event Types

| Type | Description |
|------|-------------|
| CALL | Function call with location, caller, args |
| RETURN | Function return with return value info |
| CREATE | Object creation (PyRefTracer) |
| DESTROY | Object destruction with creation context |

## C Module Features

- **C23 standard**: `nullptr`, `constexpr`, `static_assert`, `unreachable()`
- **Python 3.14**: Multi-phase init, `Py_MOD_GIL_USED`
- **Low complexity**: All functions < 25 cognitive complexity
- **Memory safe**: Ownership model with `_owned`/`_ref` suffixes

## Development

```bash
# Setup
make dev-setup

# Test
make test

# Lint
make lint
```

## License

Apache License 2.0
