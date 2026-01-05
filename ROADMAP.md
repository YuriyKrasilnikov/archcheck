# archcheck Roadmap

## Completed

### Phase 0: C Tracking Module

C extension for runtime data flow tracking.

**Features:**
- PyRefTracer API (CREATE/DESTROY)
- Frame evaluator hook (CALL/RETURN)
- Hash table: obj_id → CreationInfo
- C23: nullptr, constexpr, static_assert, unreachable
- Python 3.14: multi-phase init, Py_MOD_GIL_USED

### Phase 1: Reports & Visualization

**Domain:**
- Location, EventType, CallEvent, ReturnEvent, CreateEvent, DestroyEvent
- TrackingResult, ArchCheckError, ConversionError

**Infrastructure:**
- tracking.py — C binding with FAIL-FIRST conversion

**Application:**
- TrackerService — track(), track_context()
- ConsoleReporter, JsonReporter
- GroupStrategy — ByType, ByFile, ByFunc

### Phase 2: Filtering & Analysis

**Domain:**
- CallEdge, CallGraph (edges + unmatched)
- ObjectLifecycle, ObjectFlow (objects + orphan_destroys)
- FilterConfig, AnalysisResult

**Infrastructure:**
- Filter type alias (PEP 695)
- include_types(), exclude_types()
- include_paths(), exclude_paths() — fnmatch
- all_of(), any_of(), negate()

**Application:**
- AnalyzerService — filter(), build_call_graph(), build_object_flow(), analyze()

**Key decision:** Path filters apply only to CALL/RETURN (not CREATE/DESTROY) — object ID is global.

---

## Planned

### Phase 3: Static Analysis

- AST parsing → Module, Class, Function
- StaticCallGraph from source code
- MergedCallGraph (static + runtime)

### Phase 4: Validation

- ArchitectureConfig — layers, allowed_imports, pure_layers
- Validators — cycle, boundary, fan_out, purity
- CheckerService — validate all rules

### Phase 5: DSL & pytest

- Fluent API: arch.modules().in_layer("x").should().not_import("y")
- pytest fixtures: arch, arch_codebase, arch_config

---

## Backlog

- Watch mode
- TOML config
- HTML reports
- VS Code extension
- Memory leak detection
