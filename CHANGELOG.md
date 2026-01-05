# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

**C Tracking Module**
- C23 standard: `nullptr`, `constexpr`, `static_assert`, `unreachable()`
- GCC 15.2.0 required
- Multi-phase module init with `Py_MOD_GIL_USED` for Python 3.14
- PyRefTracer API for CREATE/DESTROY events
- Frame evaluator hook for CALL/RETURN events
- Hash table for object creation tracking
- Cognitive complexity < 25 for all functions
- Headers: constants.h, types.h, memory.h, errors.h, events.h, output.h

**Domain Layer**
- `Location` — file, line, func (frozen dataclass)
- `EventType` — CALL, RETURN, CREATE, DESTROY
- `CallEvent` — location, caller, args
- `ReturnEvent` — location, return value info
- `CreateEvent` — object id, type name, location
- `DestroyEvent` — object id, type name, creation context
- `TrackingResult` — events tuple, output errors
- `ArchCheckError`, `ConversionError` — FAIL-FIRST exceptions

**Infrastructure Layer**
- `tracking.py` — C binding with domain conversion
- `start()`, `stop()`, `count()`, `is_active()`, `get_origin()`
- FAIL-FIRST validation on C output

**Application Layer**
- `TrackerService` — `track()`, `track_context()`
- `ConsoleReporter` — rich-based console output
- `JsonReporter` — machine-readable JSON
- `GroupStrategy` — ByTypeStrategy, ByFileStrategy, ByFuncStrategy

### Changed

- License changed from MIT to Apache 2.0
- Complete architecture rewrite
- Removed old domain model, validators, collectors, analyzers
- Removed presentation layer (DSL, pytest plugin) — will be reimplemented in Phase 5

## [0.1.0] - Initial

### Added
- Initial project structure
