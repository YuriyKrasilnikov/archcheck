# Contributing to archcheck

## Philosophy

```
FAIL-FIRST       : Invalid → Exception immediately, NO fallbacks
IMMUTABLE        : frozen dataclasses, tuple, frozenset
NO type: ignore  : Fix types, don't suppress
C23 ONLY         : nullptr, constexpr, static_assert, unreachable
```

## Architecture

```
src/archcheck/
├── domain/           # Pure types (stdlib only)
│   ├── events.py     # Location, EventType, *Event, TrackingResult
│   ├── graphs.py     # CallEdge, CallGraph, ObjectFlow, FilterConfig
│   └── exceptions.py # ArchCheckError, ConversionError
├── infrastructure/   # External adapters
│   ├── tracking.py   # C module binding
│   └── filters/      # Filter functions (pure, stateless)
└── application/      # Business logic
    ├── services/     # TrackerService, AnalyzerService
    └── reporters/    # Console, JSON reporters

c/
├── _tracking.c       # Main C module
└── tracking/         # Headers (single responsibility each)
```

## C Code Standards

- **C23 required** (GCC 15+)
- **nullptr** instead of NULL
- **constexpr** for constants
- **static_assert** for invariants
- **unreachable()** for impossible branches
- **Cognitive complexity < 25**

## Development

```bash
make dev-setup    # Install + pre-commit
make test         # All tests
make lint         # ruff + mypy
make check        # lint + test
```

## Commit Messages

[Conventional Commits](https://www.conventionalcommits.org/):

```
feat(tracking): add new event type
fix(reporters): handle empty events
refactor(domain): extract Location
```

## Pull Request Checklist

- [ ] Tests pass (`make test`)
- [ ] Lint passes (`make lint`)
- [ ] FAIL-FIRST validation in new types
- [ ] C code uses C23 features
- [ ] No `type: ignore` or `noqa`
- [ ] `CHANGELOG.md` updated (new feature / fix / breaking change)
- [ ] `ROADMAP.md` updated (if milestone completed)
- [ ] `README.md` updated (if public API changed)

## License

Apache License 2.0
