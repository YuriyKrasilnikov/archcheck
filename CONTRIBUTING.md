# Contributing to archcheck

Thank you for your interest in contributing to archcheck!

## Philosophy

Before contributing, understand the core philosophy:

```
FAIL-FIRST: Invalid → Exception immediately
NO FALLBACKS: No "let's try another way"
NO LEGACY: Modern Python 3.14+
MAXIMUM PURITY: Pure core, dirty periphery
```

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YourUsername/archcheck.git
   cd archcheck
   ```

3. **Set up development environment**:
   ```bash
   make dev-setup
   ```

4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration
```

### Code Quality

Before committing, ensure your code passes all checks:

```bash
# Format code
make format

# Run linters
make lint

# Type checking
make type-check
```

### Code Style

- **Python 3.14+ only** — use modern Python features
- **Type hints required** — strict mypy mode
- **Line length**: 100 characters
- **No ignore rules** — fix issues, don't suppress them
- **Docstrings**: Google style for public APIs

Example:
```python
def check_import_rule(
    module: Module,
    forbidden: frozenset[str],
) -> RuleResult:
    """Check module imports against forbidden patterns.

    Args:
        module: Module to check
        forbidden: Set of forbidden import patterns

    Returns:
        Result containing any violations found

    Raises:
        ParsingError: If module AST is invalid
    """
    ...
```

## Architecture

archcheck follows Hexagonal Architecture and verifies itself:

```
src/archcheck/
├── domain/           # Pure core (no external deps)
│   ├── model/        # Module, Class, Function, Rule, Violation
│   ├── rules/        # Import, Naming, Purity, DI rules
│   ├── predicates/   # Reusable predicates
│   ├── exceptions/   # Domain exceptions
│   └── ports/        # ABC interfaces
├── application/      # Use cases, services
├── infrastructure/   # Adapters, analyzers
├── presentation/     # pytest plugin, Fluent API
└── shared/           # Common utilities
```

**Dependency rules:**
- `domain` → only stdlib
- `application` → domain
- `infrastructure` → domain, application
- `presentation` → all

## Testing Guidelines

- **Write tests first** (TDD encouraged)
- **Unit tests**: Domain must have >90% coverage
- **Use fixtures**: Share test data via pytest fixtures
- **No mocks in domain tests** — domain is pure

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add purity analyzer for function side-effects
fix: handle nested class inheritance resolution
docs: add hexagonal architecture example
test: add tests for DI rule violations
refactor: extract predicate composition
perf: cache AST parsing results
```

## Pull Request Process

1. **Update tests** — ensure all tests pass
2. **Run all checks** — `make lint` must pass
3. **Write clear PR description**
4. **Link related issues**

## Questions?

- Open an [issue](https://github.com/YuriyKrasilnikov/archcheck/issues)
- Start a [discussion](https://github.com/YuriyKrasilnikov/archcheck/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
