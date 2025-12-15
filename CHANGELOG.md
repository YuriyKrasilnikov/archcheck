# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

**Architecture**
- Three-layer data architecture (Dynamic → Config → Rules)
- Extensibility via Protocol + Composition pattern
- Registry pattern for internal extensibility

**Edge Architecture (Phase 3)**
- `EdgeNature` enum: DIRECT, PARAMETRIC, INHERITED, FRAMEWORK
- `CallInstance` — single call with Location, CallType, count
- `FunctionEdge` — edge between functions with nature classification
- `LibEdge` — edge from app to library
- `MergedCallGraph` rewritten with O(1) indexed access:
  - `_idx_by_pair`: (caller, callee) → FunctionEdge
  - `_idx_by_caller`: caller → frozenset[callees]
  - `_idx_by_callee`: callee → frozenset[callers]
  - `_idx_by_nature`: EdgeNature → tuple[FunctionEdge]
  - `direct_edges`: precomputed DIRECT edges only
  - `edge_pairs`: for cycle detection
- `EdgeClassifier` — classifies edge nature based on imports and frameworks
- `build_module_imports()` — extracts imports per module from Codebase

**Domain Types (Phase 1.1)**
- Runtime types: CallSite, LibCallSite, CalleeKind, CalleeInfo
- Runtime graphs: RuntimeCallGraph (thread-safe), AsyncCallGraph, CombinedCallGraph
- Merged types: MergedCallGraph, HiddenDep, HiddenDepType, EntryPointCategories
- Validation types: LayerViolation, CheckResult
- Coverage types: FunctionInfo, CoverageReport
- Configuration: ArchitectureConfig with extras for user extensions
- Static analysis: StaticCallGraph, StaticCallEdge, CallType

**Ports (Protocols)**
- VisitorProtocol — contract for AST visitors
- ValidatorProtocol — contract for validators with from_config()
- ReporterProtocol — contract for reporters (NOT rich-specific)
- CollectorProtocol — contract for runtime collectors

**Validators**
- CycleValidator — always enabled, uses graphlib.TopologicalSorter
- BoundaryValidator — if config.allowed_imports
- PurityValidator — if config.pure_layers
- CouplingValidator — if config.max_fan_out
- DIAwareValidator — understands DI pattern (impl→interface OK)

**Runtime Collectors (Python 3.14)**
- CallGraphCollector — sys.monitoring (PEP 669)
- AsyncCallGraphCollector — asyncio.capture_call_graph()
- RuntimeArchCollector — combined sync + async

**Reporters**
- PlainTextReporter — stdlib only
- JSONReporter — machine-readable output

**Discovery**
- discover_layers() — from filesystem
- discover_modules() — from filesystem
- load_known_libs() — from requirements/*.txt

**Merge**
- build_merged_graph() — AST + Runtime with edge aggregation and classification
- detect_hidden_deps() — Runtime ∖ AST (only DYNAMIC now)

### Changed

- `_BUILTINS` — discover via `frozenset(dir(builtins))` instead of hardcode
- `detect_cycles()` — use stdlib `graphlib.TopologicalSorter`
- `RuleCategory` — extended with BOUNDARIES, COUPLING, COHESION, ISOLATION, CONTRACTS, QUALITY, RUNTIME
- `ArchitectureDefinition` — frozen + Builder pattern
- `ReporterPort` — changed to Protocol-based (CheckResult instead of Violation/Summary)
- `build_merged_graph()` — now requires `module_imports` and `known_frameworks` parameters
- `HiddenDepType` — only DYNAMIC remains (PARAMETRIC/FRAMEWORK moved to EdgeNature)
- Validators now use `direct_edges` (BoundaryValidator, DIAwareValidator)
- CycleValidator now uses `edge_pairs` for O(1) access
- `_registry.py` uses `type[BaseValidator]` instead of `type[ValidatorProtocol]`

### Fixed

- RuleValidationError — added FAIL-FIRST validation in __init__
- FunctionEdge — forbids self-loops (caller_fqn == callee_fqn → ValueError)

## [0.1.0] - Initial

### Added
- Initial project structure (Hexagonal Architecture)
- Domain model: Module, Class, Function, Import, Location
- Domain model: Rule, Violation, RuleResult
- Domain model: DiGraph with FAIL-FIRST invariants
- AST analyzers: import, decorator, body, function, class
- Basic predicates: module, class, function
- Fluent API skeleton
- pytest plugin skeleton
