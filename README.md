# archcheck

Python architecture testing framework with deep AST analysis.

## Philosophy

```
FAIL-FIRST: Invalid � Exception immediately
NO FALLBACKS: No "let's try another way"
NO LEGACY: Modern Python 3.14+
MAXIMUM PURITY: Pure core, dirty periphery
```

## Features

- **Deep AST analysis**  not just imports, but class structure, inheritance, decorators, type hints
- **Function purity checking**  I/O, random, time, env access detection
- **FAIL-FIRST policy**  no fallbacks, no silent errors
- **DI-awareness**  constructor injection vs service locator detection
- **Built-in architecture patterns**  Hexagonal, Clean, Layered
- **Fluent DSL API**  ArchUnit-style rules
- **pytest plugin**  seamless integration

## Installation

```bash
pip install archcheck
```

## Quick Start

```python
from archcheck import ArchCheck

arch = ArchCheck.analyze("./src", package="myapp")

# Domain must not import infrastructure
(
    arch.modules()
    .in_package("myapp.domain")
    .should()
    .not_import("myapp.infrastructure")
    .because("Domain must be independent")
    .assert_check()
)

# Domain functions must be pure
(
    arch.functions()
    .in_module("myapp.domain.model.*")
    .should()
    .be_pure()
    .assert_check()
)

# Hexagonal architecture
(
    arch.hexagonal_architecture()
    .domain("myapp.domain")
    .application("myapp.services")
    .infrastructure("myapp.infrastructure")
    .presentation("myapp.api")
    .check()
    .assert_passed()
)
```

## pytest Integration

```python
# tests/test_architecture.py
import pytest
from archcheck import ArchCheck

@pytest.fixture(scope="session")
def arch():
    return ArchCheck.analyze("./src", package="myapp")

def test_domain_is_pure(arch):
    (
        arch.functions()
        .in_module("myapp.domain.*")
        .should()
        .be_pure()
        .not_call("print", "open", "requests.*")
        .assert_check()
    )
```

## Comparison

| Feature | import-linter | pytest-archon | PyTestArch | **archcheck** |
|---------|---------------|---------------|------------|---------------|
| Import checking | Yes | Yes | Yes | Yes |
| Inheritance checking | No | No | No | **Yes** |
| Decorator checking | No | No | No | **Yes** |
| Type hints checking | No | No | No | **Yes** |
| Function purity | No | No | No | **Yes** |
| DI analysis | No | No | No | **Yes** |
| FAIL-FIRST policy | No | No | No | **Yes** |
| Hexagonal/Clean presets | No | No | No | **Yes** |

## License

MIT
