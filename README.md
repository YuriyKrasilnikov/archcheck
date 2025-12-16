# archcheck

[![Tests](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/test.yml/badge.svg)](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/test.yml)
[![Lint](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/lint.yml/badge.svg)](https://github.com/YuriyKrasilnikov/archcheck/actions/workflows/lint.yml)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-blue.svg)](http://mypy-lang.org/)

Architecture testing framework for Python 3.14. Static + Runtime analysis. Extensible via Protocols.

## Philosophy

| Principle | Implementation |
|-----------|----------------|
| **FAIL-FIRST** | Invalid input → Exception. No fallbacks. No "try another way". |
| **NO LEGACY** | Python 3.14+ only. Uses `sys.monitoring` (PEP 669), `asyncio.capture_call_graph`, `graphlib`. |
| **DISCOVER > HARDCODE** | Builtins via `dir(builtins)`. Layers from filesystem. Libs from requirements. |
| **IMMUTABLE** | `frozen dataclasses`, `tuple`, `frozenset`, `MappingProxyType`. |
| **COMPOSITION > INHERITANCE** | User extends via Protocol conformance, not subclassing. |
| **EXPLICIT > MAGIC** | No decorators that change behavior. Config enables features explicitly. |
| **THREAD-SAFE** | RuntimeCallGraph protected by Lock. Collectors are reentrant. |

## Features

```
ANALYSIS
├── Static     AST parsing → imports, classes, functions, calls
├── Runtime    sys.monitoring (PEP 669) → actual call graph
├── Async      asyncio.capture_call_graph → task dependencies
└── Merged     Static structure + Runtime counts + Hidden deps

EDGE CLASSIFICATION
├── DIRECT      caller imports callee module
├── PARAMETRIC  caller receives callee as parameter (HOF, callback)
├── INHERITED   super().method() calls
└── FRAMEWORK   framework calls app code (pytest→test, fastapi→handler)

VALIDATION
├── CycleValidator       graphlib.TopologicalSorter, always enabled
├── BoundaryValidator    layer import rules, if config.allowed_imports
├── DIAwareValidator     impl→interface via DI is OK, if registry available
├── PurityValidator      no side effects in pure layers, if config.pure_layers
└── CustomValidator      user-defined via ValidatorProtocol

DSL (Fluent API)
├── Queries      modules(), classes(), functions(), edges()
├── Filters      in_layer(), matching(), named(), that(), async_only()
├── Assertions   not_import(), be_in_layer(), not_cross_boundary()
├── Execution    assert_check() | collect() | is_valid()
└── Patterns     * (segment), ** (any), ? (char), .** (subtree)

PYTEST INTEGRATION
├── Fixtures     arch, arch_with_graph, arch_checker, arch_config
├── Config       pytest.ini: arch_source_dir, arch_package
└── Scope        session (parsed once, reused)
```

## Installation

```bash
pip install archcheck
```

## Quick Start

```python
# test_architecture.py

def test_hexagonal_layers(arch):
    """Domain must not import infrastructure."""
    arch.modules().in_layer("domain").should().not_import(
        "myapp.infrastructure.**"
    ).assert_check()

def test_repositories_naming(arch):
    """*Repository classes must be in infrastructure."""
    arch.classes().named("*Repository").should().be_in_layer(
        "infrastructure"
    ).assert_check()

def test_no_forbidden_calls(arch_with_graph):
    """Domain must not call infrastructure directly."""
    arch_with_graph.edges().from_layer("domain").to_layer("infrastructure").should().not_cross_boundary().assert_check()
```

## DSL Reference

### Entry Points

```python
from archcheck import ArchCheck

arch = ArchCheck(codebase)                    # static analysis only
arch = ArchCheck(codebase, merged_graph)      # with edge support
```

### Queries

| Method | Returns | Operates on |
|--------|---------|-------------|
| `modules()` | `ModuleQuery` | `Module` |
| `classes()` | `ClassQuery` | `Class` |
| `functions()` | `FunctionQuery` | `Function` |
| `edges()` | `EdgeQuery` | `FunctionEdge` (requires graph) |

### Filters

```
ModuleQuery
├── in_layer(name)           module in layer
├── in_package(prefix)       module.name.startswith(prefix)
├── matching(pattern)        glob pattern on module.name
└── that(predicate)          custom filter

ClassQuery
├── in_layer(name)
├── in_package(prefix)
├── matching(pattern)
├── named(pattern)           glob pattern on class.name only
├── extending(base)          class extends base
├── implementing(protocol)   class implements protocol
└── that(predicate)

FunctionQuery
├── in_layer(name)
├── in_module(pattern)
├── matching(pattern)
├── named(pattern)
├── async_only()             only async functions
├── methods_only()           only methods (not module-level)
├── module_level_only()      only module-level (not methods)
└── that(predicate)

EdgeQuery
├── from_layer(name)         caller in layer
├── to_layer(name)           callee in layer
├── crossing_boundary()      caller_layer ≠ callee_layer
├── with_nature(nature)      EdgeNature filter
├── direct_only()            nature == DIRECT
└── that(predicate)
```

### Assertions

```
ModuleAssertion
├── not_import(*patterns)    no imports matching patterns
├── only_import(*patterns)   imports ONLY from patterns
└── be_in_layer(name)

ClassAssertion
├── extend(base)             must extend base
├── implement(protocol)      must implement protocol
├── be_in_layer(name)
└── have_max_methods(n)      ≤ n public methods

FunctionAssertion
├── not_call(*patterns)      no calls matching patterns
├── only_call(*patterns)     calls ONLY to patterns
└── be_in_layer(name)

EdgeAssertion
├── not_cross_boundary()     caller_layer == callee_layer
└── be_allowed(mapping)      edge allowed by layer→layers mapping
```

### Execution

| Method | Returns | Behavior |
|--------|---------|----------|
| `assert_check()` | `None` | Raises `ArchitectureViolationError` if violations |
| `collect()` | `tuple[Violation, ...]` | Returns all violations |
| `is_valid()` | `bool` | `True` if no violations |

### Pattern Syntax

```
*     one segment (no dots)     foo.*.bar  → foo.x.bar ✓, foo.x.y.bar ✗
**    any segments              foo.**     → foo ✓, foo.bar ✓, foo.bar.baz ✓
?     one character             fo?        → foo ✓, fo ✗
.**   module + all children     foo.**     → foo ✓, foo.bar ✓ (but not foobar)
```

## pytest Integration

### Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
arch_source_dir = "src/myapp"
arch_package = "myapp"
```

### Fixtures

| Fixture | Type | Description |
|---------|------|-------------|
| `arch` | `ArchCheck` | Static analysis. `modules()`, `classes()`, `functions()`. |
| `arch_with_graph` | `ArchCheck` | With MergedCallGraph. Supports `edges()`. |
| `arch_checker` | `ArchChecker` | Facade. Runs validators (cycles, boundaries). |
| `arch_codebase` | `Codebase` | Parsed source code. |
| `arch_config` | `ArchitectureConfig` | Override in conftest.py. |
| `arch_merged_graph` | `MergedCallGraph` | Static-only call graph. |

### Custom Config

```python
# conftest.py
import pytest
from archcheck import ArchitectureConfig

@pytest.fixture(scope="session")
def arch_config() -> ArchitectureConfig:
    return ArchitectureConfig(
        allowed_imports={
            "domain": frozenset(),                              # imports nothing
            "application": frozenset({"domain"}),               # imports domain
            "infrastructure": frozenset({"domain", "application"}),
        },
        pure_layers=frozenset({"domain"}),                      # no side effects
        known_frameworks=frozenset({"pytest", "fastapi"}),      # framework detection
    )
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: DYNAMIC (always works, no config required)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ discover_layers(app_dir)        → frozenset[str]                            │
│ discover_modules(app_dir)       → frozenset[str]                            │
│ load_known_libs(requirements)   → frozenset[str]                            │
│ StaticCallGraph                 ← AST parsing                               │
│ RuntimeCallGraph                ← sys.monitoring (PEP 669)                  │
│ AsyncCallGraph                  ← asyncio.capture_call_graph                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: CONFIGURATION (optional, enables validators)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ allowed_imports    → BoundaryValidator                                      │
│ pure_layers        → PurityValidator                                        │
│ max_fan_out        → CouplingValidator                                      │
│ known_frameworks   → EdgeClassifier (FRAMEWORK nature)                      │
│ extras             → user's CustomValidator                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: RULES (adapts to config)                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ ALWAYS: detect_cycles          graphlib.TopologicalSorter                   │
│ ALWAYS: build_merged_graph     Static + Runtime + EdgeNature                │
│ IF config: validators          BoundaryValidator, DIAwareValidator, ...     │
│ OUTPUT: CheckResult            violations, coverage, merged_graph           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### MergedCallGraph Structure

```
MergedCallGraph
├── nodes: frozenset[str]                    all function FQNs
├── edges: tuple[FunctionEdge, ...]          app→app edges
├── lib_edges: tuple[LibEdge, ...]           app→lib edges
├── hidden_deps: frozenset[HiddenDep]        runtime-only (dynamic dispatch)
│
├── Index: _idx_by_pair      O(1) lookup by (caller, callee)
├── Index: _idx_by_caller    O(1) get all callees of function
├── Index: _idx_by_callee    O(1) get all callers of function
├── Index: _idx_by_nature    O(1) filter by EdgeNature
│
├── Property: direct_edges   precomputed DIRECT edges only
└── Property: edge_pairs     for cycle detection
```

## Extensibility

### Custom Validator

```python
from archcheck import ValidatorProtocol, RuleCategory, Violation

class MaxDepthValidator:
    category = RuleCategory.CUSTOM

    def __init__(self, max_depth: int) -> None:
        self._max_depth = max_depth

    def validate(self, graph, config) -> tuple[Violation, ...]:
        # analyze graph, return violations
        ...

    @classmethod
    def from_config(cls, config, registry=None):
        depth = config.extras.get("max_depth")
        return cls(depth) if depth else None
```

### Custom Reporter

```python
from archcheck import ReporterProtocol, CheckResult

class SlackReporter:
    def report(self, result: CheckResult) -> None:
        if not result.passed:
            slack.post(channel, format_violations(result.violations))
```

### Custom Predicate

```python
def is_repository(cls):
    return cls.name.endswith("Repository")

arch.classes().that(is_repository).should().be_in_layer("infrastructure").assert_check()
```

## Comparison

| Feature | import-linter | pytest-archon | PyTestArch | **archcheck** |
|---------|:-------------:|:-------------:|:----------:|:-------------:|
| Python version | 3.8+ | 3.8+ | 3.8+ | **3.14+** |
| Import checking | ✓ | ✓ | ✓ | ✓ |
| Runtime analysis | ✗ | ✗ | ✗ | **✓** sys.monitoring |
| Async analysis | ✗ | ✗ | ✗ | **✓** asyncio.capture |
| Edge classification | ✗ | ✗ | ✗ | **✓** DIRECT/PARAMETRIC/INHERITED/FRAMEWORK |
| DI-aware | ✗ | ✗ | ✗ | **✓** |
| Hidden deps | ✗ | ✗ | ✗ | **✓** |
| Fluent DSL | partial | ✗ | ✓ | **✓** |
| Pattern matching | basic | basic | basic | **✓** `*`, `**`, `?`, `.**` |
| Call graph | ✗ | ✗ | ✗ | **✓** indexed O(1) |
| Extensible | config | ✗ | ✗ | **✓** Protocol |
| pytest fixtures | ✗ | ✓ | ✓ | **✓** 6 fixtures |
| FAIL-FIRST | ✗ | ✗ | ✗ | **✓** |
| Immutable types | ✗ | ✗ | ✗ | **✓** |
| Thread-safe | ✗ | ✗ | ✗ | **✓** |

## License

MIT
