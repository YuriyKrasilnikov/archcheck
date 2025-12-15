# Contributing to archcheck

## Philosophy

```
FAIL-FIRST       : Invalid → Exception immediately, NO fallbacks
DISCOVER > HARDCODE : dir(builtins), filesystem, graphlib — NOT hardcoded lists
EXTENSIBLE       : Protocol + Composition for users, Registry for developers
IMMUTABLE        : frozen dataclasses, tuple, frozenset everywhere
NO type: ignore  : Fix types, don't suppress
```

## Architecture

### Three-Layer Data Architecture

```
Layer 1: DYNAMIC (archcheck discovers, ALWAYS works)
         discover_layers(), StaticCallGraph, RuntimeCallGraph

Layer 2: CONFIGURATION (user optional)
         ArchitectureConfig — None = disabled, {...} = enabled

Layer 3: RULES (archcheck validates, adapts to config)
         validators activated by config fields
```

### Hexagonal Structure

```
src/archcheck/
├── domain/           # Pure core (stdlib only)
│   ├── model/        # Types: CallSite, LayerViolation, ArchitectureConfig
│   ├── ports/        # Protocols: VisitorProtocol, ValidatorProtocol, ReporterProtocol
│   ├── predicates/   # Specification pattern
│   └── exceptions/   # Domain exceptions
│
├── application/      # Business logic
│   ├── discovery/    # Layer 1: discover_layers, load_known_libs
│   ├── collectors/   # Layer 1: sys.monitoring, asyncio.capture_call_graph
│   ├── static_analysis/  # Layer 1: AST-based analysis
│   ├── merge/        # MergedCallGraph = AST + Runtime
│   ├── validators/   # Layer 3: CycleValidator, BoundaryValidator, etc.
│   ├── visitors/     # AST visitors
│   ├── reporters/    # PlainTextReporter, JSONReporter
│   └── services/     # ArchChecker facade
│
├── infrastructure/   # Adapters
│   ├── analyzers/    # AST analyzers
│   └── adapters/     # Parser adapters
│
└── presentation/     # User-facing
    ├── pytest_plugin/
    └── dsl/          # Fluent API
```

## Extensibility

### For Users (Protocol + Composition)

Users extend archcheck by:
1. Implementing Protocol (VisitorProtocol, ValidatorProtocol, ReporterProtocol)
2. Passing instances to ArchChecker constructor

```python
# User implements
class MyValidator:
    category = RuleCategory.CUSTOM

    def validate(self, graph, config) -> tuple[Violation, ...]:
        ...

    @classmethod
    def from_config(cls, config, registry=None) -> Self | None:
        if config.extras.get("my_feature") is None:
            return None  # disabled
        return cls()

# User uses
checker = ArchChecker(
    codebase,
    validators=[*default_validators(), MyValidator()],
)
```

### For Developers (Registry Pattern)

Adding new component:

**Add Validator:**
```
1. application/validators/[name]_validator.py — create file
2. application/validators/_registry.py:
   + from .new_validator import NewValidator
   + _ALL_VALIDATORS += (NewValidator,)
3. domain/model/configuration.py — add config field (optional)
4. tests/
```

**Add Visitor:**
```
1. application/visitors/[name]_visitor.py — create file
2. application/visitors/_registry.py — add to tuple
3. tests/
```

**Add Collector:**
```
1. application/collectors/[name]_collector.py
2. domain/model/[graph_type].py — new type
3. application/collectors/combined.py — integrate
4. tests/
```

**Add Domain Type:**
```
1. domain/model/[name].py — frozen dataclass with FAIL-FIRST __post_init__
2. domain/model/__init__.py — re-export
3. tests/
```

## Code Style

### FAIL-FIRST Validation

```python
@dataclass(frozen=True, slots=True)
class CallSite:
    module: str
    function: str
    line: int

    def __post_init__(self) -> None:
        if not self.module:
            raise ValueError("module must not be empty")
        if not self.function:
            raise ValueError("function must not be empty")
        if self.line < 1:
            raise ValueError("line must be >= 1")
```

### Discover Instead of Hardcode

```python
# BAD: hardcoded
_BUILTINS = frozenset({"abs", "all", "any", ...})  # 100+ lines

# GOOD: discover
import builtins
_BUILTINS = frozenset(dir(builtins)) | _TYPE_HINT_NAMES
```

### Use stdlib

```python
# BAD: custom Tarjan
def detect_cycles(graph): ...  # 50 lines

# GOOD: stdlib graphlib
from graphlib import TopologicalSorter, CycleError

def detect_cycles(graph):
    ts = TopologicalSorter(adjacency)
    try:
        tuple(ts.static_order())
        return ()
    except CycleError as e:
        return (frozenset(e.args[1]),)
```

### Protocol over ABC

```python
# Prefer Protocol for duck typing
class ValidatorProtocol(Protocol):
    category: RuleCategory

    def validate(self, graph, config) -> tuple[Violation, ...]: ...

    @classmethod
    def from_config(cls, config, registry=None) -> Self | None: ...
```

## Development Workflow

```bash
# Setup
make dev-setup

# Tests
make test          # all
make test-unit     # unit only
make test-mut      # mutation testing

# Quality
make lint          # ruff
make type-check    # mypy --strict
make format        # ruff format

# All checks
make check         # lint + type-check + test
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(validators): add CohesionValidator for class width checks
fix(collectors): handle thread-safety in RuntimeCallGraph
refactor(domain): extract CallSite from RuntimeCallGraph
test(validators): add tests for DIAwareValidator
docs: update README with three-layer architecture
```

## Pull Request Checklist

- [ ] Tests pass (`make test`)
- [ ] Type check passes (`make type-check`)
- [ ] Lint passes (`make lint`)
- [ ] 100% coverage for new code
- [ ] FAIL-FIRST validation in new types
- [ ] Protocol-based if adding new extension point
- [ ] Registry updated if adding new validator/visitor
- [ ] Documentation updated

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
