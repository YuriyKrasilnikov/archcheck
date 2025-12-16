# archcheck

[![Tests](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/test.yml/badge.svg)](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/test.yml)
[![Lint](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/lint.yml/badge.svg)](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/lint.yml)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue.svg)](http://mypy-lang.org/)

Extensible framework для статического + runtime анализа архитектуры Python 3.14.

## Philosophy

```
FAIL-FIRST      : Invalid → Exception immediately, NO fallbacks
DISCOVER > HARDCODE : dir(builtins), filesystem structure, graphlib
EXTENSIBLE      : Protocol + Composition (user extends via conformance)
IMMUTABLE       : frozen dataclasses, tuple, frozenset
```

## Features

- **Three-layer data architecture** — Dynamic (always works) → Config (optional) → Rules (adapts)
- **Static + Runtime analysis** — AST + sys.monitoring (PEP 669) + asyncio.capture_call_graph
- **Extensible** — user adds visitors/validators/reporters via Protocol conformance
- **DI-aware validation** — understands impl→interface through DI is OK
- **Cycle detection** — via stdlib graphlib.TopologicalSorter
- **MergedCallGraph** — AST structure + Runtime filter/counts + hidden deps detection
- **pytest plugin** — fixtures, hooks, session reporting
- **Fluent DSL** — arch.modules().should().not_import()

## Installation

```bash
pip install archcheck
```

## Quick Start

### Minimal (Layer 1 only — always works)

```python
from archcheck import ArchChecker

# No config needed — cycles detection works
checker = ArchChecker.with_defaults(codebase)
result = checker.check()

if not result.passed:
    for v in result.violations:
        print(v.message)
```

### With Configuration (Layer 2 enables features)

```python
from archcheck import ArchChecker, ArchitectureConfig

config = ArchitectureConfig(
    allowed_imports={
        "domain": frozenset(),  # domain imports nothing
        "services": frozenset({"domain", "interfaces"}),
        "adapters": frozenset({"domain", "interfaces"}),
    },
    pure_layers=frozenset({"domain"}),
    composition_root=frozenset({"myapp.core.container"}),
)

checker = ArchChecker.from_config(codebase, config)
result = checker.check()
assert result.passed
```

### Fluent DSL

```python
# test_architecture.py
def test_domain_isolation(arch):
    """Domain layer must not import infrastructure."""
    arch.modules().in_layer("domain").should().not_import(
        "myapp.infrastructure.**"
    ).assert_check()

def test_repositories_in_infrastructure(arch):
    """All *Repository classes must be in infrastructure layer."""
    arch.classes().named("*Repository").should().be_in_layer(
        "infrastructure"
    ).assert_check()

def test_async_handlers_in_handlers(arch):
    """All async functions must be in handlers layer."""
    arch.functions().async_only().should().be_in_layer(
        "handlers"
    ).assert_check()

def test_no_cross_layer_calls(arch_with_graph):
    """Domain must not call infrastructure directly."""
    violations = (
        arch_with_graph.edges()
        .from_layer("domain")
        .to_layer("infrastructure")
        .direct_only()
        .should()
        .not_cross_boundary()
        .collect()
    )
    assert len(violations) == 0
```

## Extensibility

### User extends via Protocol conformance

```python
# Custom visitor
class PrintDetector:
    def __init__(self) -> None:
        self._violations: list[dict] = []

    def visit(self, tree: ast.AST) -> None:
        # detect print() calls
        ...

    @property
    def violations(self) -> Sequence[dict]:
        return self._violations

# Custom reporter (user chooses output format)
class RichReporter:
    def report(self, result: CheckResult) -> None:
        # use rich library for Tree/Table/Panel
        ...

# Usage
checker = ArchChecker(
    codebase,
    visitors=[*default_visitors(), PrintDetector()],
    reporter=RichReporter(),
)
```

### Config enables validators

```python
# None = feature disabled
# frozenset() = enabled, empty = all OK
# {...} = enabled with restrictions

config = ArchitectureConfig(
    allowed_imports=None,  # boundary checking disabled
    pure_layers=frozenset({"domain"}),  # purity checking enabled
    max_fan_out=10,  # coupling checking enabled
)
```

## Three-Layer Data Architecture

```
Layer 1: DYNAMIC (archcheck discovers, ALWAYS works)
├─ discover_layers(app_dir) → frozenset[str]
├─ discover_modules(app_dir) → frozenset[str]
├─ load_known_libs(requirements_dir) → frozenset[str]
├─ StaticCallGraph (AST)
├─ RuntimeCallGraph (sys.monitoring)
└─ AsyncCallGraph (asyncio.capture_call_graph)

Layer 2: CONFIGURATION (user optional, enables features)
├─ ArchitectureConfig.allowed_imports → BoundaryValidator
├─ ArchitectureConfig.pure_layers → PurityValidator
├─ ArchitectureConfig.max_fan_out → CouplingValidator
└─ ArchitectureConfig.extras → user's CustomValidator

Layer 3: RULES (archcheck validates, adapts to config)
├─ ALWAYS: detect_cycles (graphlib.TopologicalSorter)
├─ ALWAYS: build_merged_graph (AST + Runtime)
├─ IF config.*: specific validators
└─ OUTPUT: CheckResult (violations, coverage, merged_graph)
```

## pytest Integration

```ini
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
arch_source_dir = "src/myapp"
arch_package = "myapp"
```

```python
# conftest.py
import pytest
from archcheck import ArchitectureConfig

@pytest.fixture(scope="session")
def arch_config() -> ArchitectureConfig:
    """Override default config with your architecture rules."""
    return ArchitectureConfig(
        allowed_imports={
            "domain": frozenset(),
            "application": frozenset({"domain"}),
            "infrastructure": frozenset({"domain", "application"}),
        },
        pure_layers=frozenset({"domain"}),
        known_frameworks=frozenset({"pytest", "fastapi"}),
    )
```

```python
# test_architecture.py

def test_hexagonal_layers(arch):
    """Verify hexagonal architecture layers."""
    # Domain imports nothing from other layers
    arch.modules().in_layer("domain").should().not_import(
        "myapp.application.**", "myapp.infrastructure.**"
    ).assert_check()

    # Application doesn't import infrastructure
    arch.modules().in_layer("application").should().not_import(
        "myapp.infrastructure.**"
    ).assert_check()

def test_edge_boundaries(arch_with_graph):
    """Verify call graph respects layer boundaries."""
    arch_with_graph.edges().crossing_boundary().should().be_allowed({
        "application": frozenset({"domain"}),
        "infrastructure": frozenset({"domain", "application"}),
    }).assert_check()

def test_graph_level_validation(arch_checker):
    """Run all validators (cycles, boundaries, DI-aware)."""
    result = arch_checker.check()
    assert result.passed, f"Violations: {result.violations}"
```

### Available Fixtures

| Fixture | Description |
|---------|-------------|
| `arch` | ArchCheck for static analysis (modules, classes, functions) |
| `arch_with_graph` | ArchCheck with MergedCallGraph (supports edges()) |
| `arch_checker` | ArchChecker facade for graph-level validation |
| `arch_codebase` | Parsed Codebase |
| `arch_config` | ArchitectureConfig (override in conftest.py) |
| `arch_merged_graph` | Static-only MergedCallGraph |

## Comparison

| Feature | import-linter | pytest-archon | PyTestArch | **archcheck** |
|---------|---------------|---------------|------------|---------------|
| Import checking | Yes | Yes | Yes | Yes |
| Runtime analysis | No | No | No | **Yes** (sys.monitoring) |
| Async analysis | No | No | No | **Yes** (asyncio.capture) |
| DI-aware validation | No | No | No | **Yes** |
| Extensible (Protocol) | No | No | No | **Yes** |
| Hidden deps detection | No | No | No | **Yes** |
| MergedCallGraph | No | No | No | **Yes** |
| Function purity | No | No | No | **Yes** |
| FAIL-FIRST policy | No | No | No | **Yes** |

## License

MIT
