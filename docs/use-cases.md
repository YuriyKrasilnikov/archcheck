# Use Cases

## Connection to Philosophy

archcheck solves these cases through its design axioms:

| Axiom | What It Provides |
|-------|------------------|
| **Data Completeness** | `unresolved` + `reason` — know EVERYTHING that wasn't resolved and WHY |
| **Uniform Access** | `by_caller["x"]` works the same for all — no special cases in queries |
| **Labeling Over Partitioning** | EdgeNature is a source label, not a forced bucket; edge can be BOTH |
| **No Special Cases** | All edges are equal — user defines rules, not the library |
| **Immutability** | Result is frozen — safe to cache, compare between runs |

---

## 1. Code Path Coverage Analysis

**Problem**: Line coverage shows which lines executed, but not which **function call relationships** occurred.

**Why archcheck**: Static + runtime merge → EdgeNature classification.

```
BOTH        → call A→B exists in code AND was executed
STATIC_ONLY → call A→B exists in code but was NOT executed in this run
```

**STATIC_ONLY indicates one of:**
- Dead code (never called)
- Missing test (path not covered)
- Conditional branch (if/else not hit)
- Exception path (try/except not triggered)
- Feature flag disabled

**Action**: Analyze STATIC_ONLY edges → understand cause → add test or remove code.

**Difference from coverage.py**: coverage shows lines, archcheck shows **call relationships**.

---

## 2. Dynamic Dependency Discovery

**Problem**: HOF, callbacks, reflection create dependencies invisible in AST.

```python
def process(data, transform):  # transform = parameter
    return transform(data)     # AST sees "transform", not the concrete function

process(data, format_item)     # runtime: process → format_item
```

**Why archcheck**:
- Static: doesn't see `process → format_item` (dynamic)
- Runtime: sees the actual call
- Merge: RUNTIME_ONLY edge

**Functional Programming patterns:**
```
map(func, iterable)           → caller: enclosing function, VIA_HOF
filter(pred, iterable)        → caller: enclosing function, VIA_HOF
functools.partial(f, x)       → tracks: wrapper → original binding
sorted(key=func)              → caller: enclosing function, VIA_HOF
[f(x) for x in items]         → caller: comprehension context
lambda x: g(x)                → caller: lambda, callee: g
```

**Edge annotation**:
```
EdgeKind: DIRECT | VIA_HOF
VIA_HOF.via: "map" | "filter" | "partial" | ...
```

**Data Completeness**: No information lost. Dynamic call → RUNTIME_ONLY, not ignored.

**Action**: RUNTIME_ONLY edges → review for security, understand actual flow.

---

## 3. Architecture Layer Validation

**Problem**: Code violates layers (domain → infrastructure directly).

**Why archcheck**: Uniform Access to `by_caller`, `by_callee` without special cases.

```python
# Find all calls FROM domain
domain_calls = [e for e in merged.edges if e.caller_fqn.startswith("myapp.domain.")]

# Find violations: domain → infrastructure
violations = [e for e in domain_calls if "infrastructure" in e.callee_fqn]
```

**No Special Cases**: Library doesn't define "correct" layers. User defines rules via patterns.

**Action**: CI gate → fail build on violations.

---

## 4. Type Annotation Quality Metrics

**Problem**: Poorly typed code → static analysis ineffective.

**Why archcheck**: Data Completeness — `unresolved` with `reason`.

```
StaticCallGraph.unresolved:
  dynamic: 47    → obj.method() without type info
  builtin: 28    → print, len (expected)
  external: 2    → third-party (expected)
  undefined: 5   → errors (typos, missing import)
```

**Metric**: `dynamic / total_calls` → % of code without type info.

**Action**:
- High `dynamic` → add type annotations
- `undefined` → fix errors
- `builtin` + `external` → normal, ignore

---

## 5. Import Structure Analysis

**Problem**: Circular imports, excessive coupling.

**Why archcheck**: `Module.imports` — complete information.

```python
for name, module in codebase.modules.items():
    if len(module.imports) > 10:
        print(f"{name}: {len(module.imports)} imports → candidate for split")
```

**Data Completeness**: All imports tracked, including relative with level.

---

## 6. Test vs Production Code Paths

**Problem**: Tests cover happy path, not edge cases.

**Method**:
1. Run 1: tests only → `merged_tests`
2. Run 2: production load → `merged_prod`
3. Compare: edges in `merged_prod` but not in `merged_tests`

```python
prod_only = {(e.caller_fqn, e.callee_fqn) for e in merged_prod.edges}
test_only = {(e.caller_fqn, e.callee_fqn) for e in merged_tests.edges}
untested_prod_paths = prod_only - test_only
```

**Immutability**: Both results frozen → safe comparison.

---

## 7. Memory Leak Detection

**Problem**: Objects created but not destroyed → memory leak. Hard to find WHERE the problematic object was created.

**Why archcheck**: CREATE/DESTROY events + ObjectPool + traceback (16 frames).

```
EventGraph contains:
  CREATE:  obj_id, type_name, location, traceback[16]
  DESTROY: obj_id, type_name, location

Query:
  leaks = {c for c in creates if c.obj_id not in {d.obj_id for d in destroys}}
```

**Data Completeness**: Traceback at CREATE shows full call stack where object was created.

**Action**:
- `leaks` → list of objects without DESTROY
- `leak.traceback` → exact creation location
- Group by `type_name` → which types leak

---

## 8. Sensitive Data Flow Tracking

**Problem**: Where does `password`, `api_key`, `user_data` go? Does it leak to logs?

**Why archcheck**: Args capture for each call + ArgsPool DAG.

```
EventGraph contains:
  each CALL → args: tuple[ArgInfo, ...]
  ArgInfo: name, obj_id, type_name

Query (taint propagation):
  1. Find source: events where arg.name == "password"
  2. Track obj_id through call graph
  3. Find sinks: events where callee = "logger.info"
```

**Data Completeness**: All args preserved, content-addressed in ArgsPool.

**Action**:
- Taint source → taint sink paths
- CI gate: `password` must not reach `print`/`logger`

---

## 9. Concurrency Bug Detection

**Problem**: Race conditions, deadlocks in multi-threaded/async code.

**Why archcheck**: ExplicitEdges (PARALLEL, AWAITS, SPAWNS) + interval queries.

```
ExplicitEdges:
  PARALLEL: events in different threads with overlapping time
  AWAITS:   async waiter → awaited coroutine
  SPAWNS:   thread/task creation: spawner → spawned

Query (race detection):
  1. Find shared state access (same obj_id)
  2. Check PARALLEL edge between accessors
  3. If PARALLEL + no synchronization → potential race

Query (deadlock detection):
  1. Build AWAITS graph
  2. Find cycles → deadlock
```

**Data Completeness**: thread_id, coro_id for each event. Interval tree for overlap queries.

**Action**:
- Races: list of pairs (event1, event2) with shared access
- Deadlocks: cycles in AWAITS graph

---

## 10. Performance Hotspot Analysis

**Problem**: Where does the program spend the most time? Which call path is most expensive?

**Why archcheck**: CCT (Calling Context Tree) + time intervals.

```
CCT contains:
  path_to_root(node) → [func₁, func₂, ..., funcₙ]
  event.time = (start_ns, end_ns)

Query:
  1. For each event: duration = end_ns - start_ns
  2. Aggregate by call stack (CCT path)
  3. Sort by total_time DESC
```

**Data Completeness**: Full call stack for each event via CCT.

**Result**: Flame graph. Each CCT path → rectangle, width = total_time.

**Action**:
- Top-N hotspots by time
- Drill-down: which calls inside hotspot

---

## 11. Anomaly Detection

**Problem**: Code behaves irregularly. Which calls break the usual pattern?

**Why archcheck**: Grammar (Sequitur) + exceptions.

```
Sequitur automatically extracts patterns:
  Input:  validate → transform → store (×1000)
  Grammar: S → P^1000, P → validate transform store

Events NOT fitting grammar → exceptions:
  region.exceptions = [event₁, event₂, ...]
```

**Data Completeness**: Interior (regular) reconstructed from grammar. Exceptions stored explicitly.

**Metric**: `ε = |exceptions| / |total_events|` — anomaly rate.

**Action**:
- Low ε (< 0.001) → regular code, good
- High ε (> 0.1) → chaotic code, needs refactoring
- Specific exceptions → investigate

---

## 12. Async Task Lifecycle Analysis

**Problem**: Which asyncio Tasks were created? Which were cancelled? Why did a task hang? Where are tasks leaking?

**Why archcheck**: task_id + SPAWNS/AWAITS edges + Task events.

```
Events:
  TASK_CREATE:  task_id, task_name, creator_coro
  TASK_DONE:    task_id, result | exception
  TASK_CANCEL:  task_id, canceller, msg

Query (task leak):
  created = {e.task_id for e in events if e.kind == TASK_CREATE}
  finished = {e.task_id for e in events if e.kind in (TASK_DONE, TASK_CANCEL)}
  leaked = created - finished

Query (who cancelled task):
  cancel_event = find(events, kind=TASK_CANCEL, task_id=X)
  canceller = cancel_event.canceller  # coro/task that called cancel()

Query (task dependency graph):
  edges = [(e.waiter_task, e.awaited_task) for e in explicit_edges if e.kind == AWAITS]
  → dependency graph between tasks
```

**Data Completeness**: task_id for each event in async context. Task name preserved.

**Action**:
- Leaked tasks → find where created but not finished
- Cancel chains → who initiated cancellation
- Task graph → visualize dependencies, find circular awaits

**Difference from coro_id**: Task can be cancelled externally, has a name, can be in TaskGroup.

---

## 13. Code Characteristics Profiling

**Problem**: Understand code "character" without reading it. Regular loops? Chaotic event-driven? Predictable timing?

**Why archcheck**: Compression metadata = code characteristics.

```
archcheck collects during build:

TIMING CHARACTERISTICS:
  ρ (rho)     = correlation(predicted_time, actual_time)
  ρ > 0.7     → structured code (loops, pipelines)
  ρ < 0.3     → chaotic code (event-driven, callbacks)

PATTERN CHARACTERISTICS:
  ε (epsilon) = |exceptions| / |total_events|
  ε < 0.001   → highly regular (same patterns repeat)
  ε > 0.1     → highly irregular (each call unique)

ARGS CHARACTERISTICS:
  ArgsFactory distribution per region:
    40% CONSTANT     → loop invariants, configs
    25% FROM_RANGE   → counters, indices
    10% POLYNOMIAL   → computed sequences
    10% PERIODIC     → rotating state
    5%  RECURRENCE   → recursive patterns
    5%  GRAMMAR      → complex repeating structures
    5%  FROM_ARRAY   → unpredictable args

COMPRESSION RATIO:
  CR = |raw_events| / |compressed|
  CR > 1000×  → very predictable code
  CR < 100×   → less predictable
  CR < 10×    → essentially random
```

**Query:**
```python
profile = event_graph.code_profile()

print(f"Timing: ρ={profile.rho:.2f} ({'structured' if profile.rho > 0.5 else 'chaotic'})")
print(f"Patterns: ε={profile.epsilon:.4f} ({'regular' if profile.epsilon < 0.01 else 'irregular'})")
print(f"Compression: {profile.compression_ratio:.0f}×")
print(f"Args breakdown: {profile.args_factory_distribution}")

# Per-region analysis
for region in event_graph.regions:
    if region.rho < 0.3:
        print(f"Chaotic region: {region.key} (consider refactoring)")
```

**Data Completeness**: Metrics computed during build, always available.

**Action**:
- High ρ, low ε → code is well-structured, optimize for patterns
- Low ρ, high ε → code is chaotic, may need refactoring
- Mixed → identify chaotic regions, target for improvement
- CI gate: fail if ε > threshold (enforce code discipline)

**Difference from profilers**: cProfile shows time. archcheck shows **behavioral structure**.

---

## 14. Statistical Sampling Analysis

**Problem**: 10^9 events with args. Need statistics without O(N) iteration.

**Why archcheck**: QC Layer (Quantum-Classical) superposition.

```
QC State:
  |ψ⟩ = |common⟩ ⊗ Σᵢ αᵢ|variantᵢ⟩

Categories:
  40% constants   → Exact(v)
  30% small sets  → Enum([v₁, v₂, v₃])
  20% ranges      → Uniform(min, max)
  10% chaotic     → Empirical(samples)

Query:
  observe(|ψ⟩, "args.user_id") → distribution, not concrete value
```

**Data Completeness**: Full information preserved. QC is representation, not loss.

**Action**:
- Statistics over args without enumerating all events
- "Which user_ids occurred?" → Uniform(1, 1000) or Enum([1,2,3])
- Sample: collapse → concrete examples

---

## 15. Kinetic Edge Analysis

**Problem**: How did call count A→B change over time? When did the spike start?

**Why archcheck**: Kinetic edges — count(t) instead of static count.

```
Query:
  edge.count(t)         → call count up to time t
  edge.rate(t₁, t₂)     → calls/sec in interval
  edge.anomaly_points() → moments of sharp change

Implementation:
  checkpoints: [(t₁, c₁), (t₂, c₂), ...]
  count(t) = binary_search(checkpoints, t).cumulative
```

**Data Completeness**: All moments preserved via checkpoints.

**Action**:
- Find moment when problem started
- Correlate with external events (deploy, load spike)
- Anomaly detection: rate deviation > 3σ

---

## 16. Multi-Run Comparison

**Problem**: Compare behavior between versions, environments, configs.

**Why archcheck**: Confluent merge — O(|G₁| + |G₂|) Grammar Algebra.

```
Scenarios:
  v1.0 vs v2.0          → what changed?
  staging vs production → different paths?
  config A vs config B  → impact on call graph?

Query:
  diff = merge(graph_a, graph_b, mode=DIFF)

  diff.added_edges      → new calls
  diff.removed_edges    → removed calls
  diff.count_changes    → frequency changes
```

**Immutability**: Both graphs frozen → safe comparison without copying.

**Action**:
- Regression detection: unexpected new edges
- Dead code detection: edges removed but code still exists
- Performance comparison: count changes

---

## 17. What-If Analysis (Retroactive)

**Problem**: "What if event X hadn't happened?" without re-running.

**Why archcheck**: Retroactive operations — Insert/Delete(t).

```
Operations:
  WhatIf(t, DELETE)     → graph without event at time t
  WhatIf(t, MODIFY)     → graph with modified event
  WhatIf(t, INSERT)     → graph with added event

Query:
  original = event_graph
  hypothetical = original.what_if(t=1234567890, delete=True)

  impact = original.edges - hypothetical.edges
  # Which edges depended on the deleted event?
```

**Data Completeness**: All dependencies tracked → precise impact analysis.

**Action**:
- Root cause analysis: "if this call hadn't happened..."
- Optimization planning: "if we remove this path..."
- Security: "if attacker modifies this call..."

---

## 18. Self-Optimizing Storage

**Problem**: How to choose optimal storage mode without manual tuning?

**Why archcheck**: MDL Basin Dynamics — automatic selection.

```
Configuration Space:
  TimeMode:    COMPRESSED | HIERARCHICAL
  EventMode:   GRAMMAR | ANTI_GRAMMAR
  PoolMode:    HASHMAP | SUCCINCT
  Features:    Kinetic, Retroactive

MDL Principle:
  L(c, D) = |model(c)| + |residual(D|c)|
  c* = argmin L(c, D)

Streaming:
  Dual-write all configurations
  Prune dominated when gap sufficient
  Natural transition via basin dynamics
```

**Data Completeness**: ∀c: decode(encode(D,c)) = D — all modes lossless.

**Action**:
- No manual threshold tuning
- Automatic adaptation to data characteristics
- Exposed metrics: ρ, ε, CR for monitoring

---

## 19. Chaotic Code Handling

**Problem**: Event-driven code with ε > 0.5 — more exceptions than patterns.

**Why archcheck**: Complement Storage — Anti-Grammar.

```
Regular code (ε < 0.1):
  Grammar: S → P^1000, P → validate transform store
  Exceptions: [e₁, e₂, ...]  # few

Chaotic code (ε > 0.5):
  Anti-Grammar: G̅ generates what DID NOT happen
  Regular samples: [e₁, e₂, ...]  # few

  Actual = All_possible \ G̅.generate()
```

**Crossover**: When ε > 0.5, Anti-Grammar saves 40%+ memory.

**Data Completeness**: Both representations equivalent, choice is optimization.

**Action**:
- Automatic switch during streaming (MDL decides)
- Query interface identical (abstracted)
- Metrics expose which mode chosen

---

## 20. Succinct Symbol Tables

**Problem**: 10⁶ unique strings (file paths, func names) → 100+ MB overhead.

**Why archcheck**: Succinct Pools — 2 bits/char instead of 8.

```
Structures:
  Perfect Minimal Hash: O(1) bits/string overhead
  Succinct Trie: 2L bits for L total chars

Comparison:
  HashMap:  10⁶ × 50 chars × 20 bytes = 1 GB
  Succinct: 10⁶ × 50 chars × 2 bits  = 12.5 MB

  Savings: 80×
```

**Trade-off**: Build time O(n log n), but query remains O(1).

**Action**:
- Automatic selection via MDL (when |strings| > threshold)
- Reduced memory footprint
- Same query interface

---

## 21. Coupling & Cohesion Metrics

**Problem**: Code "feels" tangled but no quantitative measure. How coupled are modules? How cohesive internally?

**Why archcheck**: EdgeNature + by_caller/by_callee → compute standard metrics.

```
COUPLING METRICS:

  Afferent Coupling (Ca) = incoming edges to module
    Ca(M) = |{e : e.callee ∈ M, e.caller ∉ M}|
    High Ca → many dependents → hard to change

  Efferent Coupling (Ce) = outgoing edges from module
    Ce(M) = |{e : e.caller ∈ M, e.callee ∉ M}|
    High Ce → many dependencies → fragile

  Instability I = Ce / (Ca + Ce)
    I → 0: stable (many dependents, few dependencies)
    I → 1: unstable (few dependents, many dependencies)

  Coupling Between Modules (CBM):
    CBM(A, B) = |edges(A→B)| + |edges(B→A)|
    High CBM → tightly coupled → candidate for merge or interface


COHESION METRICS:

  Internal Cohesion (IC):
    IC(M) = |internal_edges| / |total_edges_involving_M|
    IC → 1: cohesive (functions call each other)
    IC → 0: incohesive (functions don't interact)

  Functional Cohesion (FC):
    FC(M) = |largest_connected_component| / |functions_in_M|
    Measures how many functions are reachable from each other
```

**Data Completeness**: All edges (BOTH + RUNTIME_ONLY) included → accurate metrics.

**Action**:
- Instability vs Abstractness plot → identify problematic modules
- High Ce + Low IC → God module, needs split
- High CBM pairs → merge or define interface
- CI gate: I < 0.8 for core modules

---

## 22. Real Architecture Discovery

**Problem**: Documentation says "3-tier" but reality unknown. What is the ACTUAL call structure?

**Why archcheck**: Runtime call graph = ground truth. Cluster by call patterns.

```
DISCOVERY ALGORITHM:

  1. BUILD ADJACENCY MATRIX:
     A[i,j] = edge_count(module_i → module_j)

  2. CLUSTER BY COUPLING:
     S[i,j] = A[i,j] + A[j,i]   (bidirectional)
     Groups = spectral_clustering(S)

  3. IDENTIFY CLUSTER ROLES:
     fan_in(C)  = Σ edges(external → C)
     fan_out(C) = Σ edges(C → external)

     fan_in >> fan_out  → CORE (depended upon)
     fan_out >> fan_in  → PERIPHERY (depends on others)
     fan_in ≈ fan_out   → MEDIATOR (orchestrates)

  4. DETECT LAYERS (if DAG):
     Topological sort → natural layering
     Cycles → coupling violations

OUTPUT:
  Layer 3 (Top):    [ui, api, cli]         ← entry points
  Layer 2 (Middle): [services, handlers]   ← business logic
  Layer 1 (Core):   [domain, models]       ← pure domain
  Layer 0 (Infra):  [db, cache, external]  ← infrastructure

  ANOMALIES:
    domain → db        (core depends on infra)
    ui → models        (skip layer)
```

**Data Completeness**: Runtime edges reveal actual dependencies, not just imports.

**Action**:
- Generate layered architecture diagram from runtime data
- Compare discovered vs intended
- Identify layer violations automatically

---

## 23. Architecture Drift Detection

**Problem**: Architecture erodes over time. How much has code drifted from intended design?

**Why archcheck**: Compare intended (config) vs actual (runtime).

```
INTENDED (user provides):
  layers:
    presentation: ["api.*", "cli.*"]
    application:  ["services.*"]
    domain:       ["domain.*", "models.*"]
    infrastructure: ["db.*", "cache.*"]

  allowed:
    presentation → application
    application → domain
    application → infrastructure
    domain → (nothing)

ACTUAL (from runtime):
  For each edge:
    src_layer = layer_of(caller)
    dst_layer = layer_of(callee)
    IF (src_layer → dst_layer) not allowed:
      violation

DRIFT METRICS:
  Violation Rate = violations / total_edges
  Severity:
    reverse (domain → application): 3
    skip_layer (api → models):      2
    cross_boundary:                 1

OUTPUT:
  total_edges: 1247
  compliant: 1189 (95.3%)
  violations: 58 (4.7%)

  worst_offenders:
    domain/user.py: 8 violations
    api/endpoints.py: 6 violations
```

**Immutability**: Compare across commits → track drift trend.

**Action**:
- CI gate: violation_rate < 5%
- Trend analysis: is drift increasing?
- Prioritize: fix reverse violations first

---

## 24. Module Role Classification

**Problem**: What role does each module play? Utility? Facade? God class?

**Why archcheck**: Fan-in/fan-out patterns reveal architectural roles.

```
CLASSIFICATION BY CALL PATTERN:

  ┌─────────────┬───────────┬────────────┬──────────────────────────────┐
  │ Role        │ Fan-in    │ Fan-out    │ Description                  │
  ├─────────────┼───────────┼────────────┼──────────────────────────────┤
  │ FACADE      │ High      │ Low        │ Simplified interface         │
  │ UTILITY     │ High      │ High       │ Shared helper (risk: God)    │
  │ ENTRY       │ Zero      │ High       │ Application entry point      │
  │ CORE        │ High      │ Zero       │ Pure domain, no dependencies │
  │ MEDIATOR    │ Medium    │ Medium     │ Orchestration layer          │
  │ ISOLATED    │ Zero      │ Zero       │ Dead code candidate          │
  │ GOD         │ Very High │ Very High  │ Everything → SPLIT NOW       │
  └─────────────┴───────────┴────────────┴──────────────────────────────┘

DETECTION:
  For each module M:
    fan_in  = |{e : callee ∈ M}|
    fan_out = |{e : caller ∈ M}|
    role = classify(fan_in, fan_out, thresholds)
```

**Data Completeness**: Runtime edges include dynamic dispatch → accurate classification.

**Action**:
- Generate module role map
- Alert on GOD modules
- Verify CORE has zero fan-out

---

## 25. Dependency Inversion Analysis

**Problem**: Do high-level modules depend on low-level details? DIP violations?

**Why archcheck**: Call edges + module classification → detect inversions.

```
DIP PRINCIPLE:
  High-level should not depend on low-level directly
  Both should depend on abstractions

DETECTION:
  1. CLASSIFY MODULES:
     high_level:   {services, handlers, use_cases}
     low_level:    {db, http, file_io, external}
     abstractions: {interfaces, protocols, abc}

  2. FIND VIOLATIONS:
     direct: high_level → low_level (bypassing interface)
       Example: services.user → db.postgres
       Should:  services.user → interfaces.repository

  3. CALCULATE DIP SCORE:
     through_abstraction = edges via interfaces
     direct_violation = edges bypassing interfaces

     DIP = through_abstraction / (through_abstraction + direct_violation)
     DIP → 1: good
     DIP → 0: bad

OUTPUT:
  DIP Score: 0.81 (81% through abstractions)

  Violations:
    services/user.py:23 → db/postgres.py:45
    handlers/api.py:67 → external/stripe.py:12
```

**Data Completeness**: Runtime shows ACTUAL dependencies, not declared.

**Action**:
- Extract interfaces where DIP violated
- CI gate: DIP_score >= 0.8
- Track DIP score trend

---

## 26. Circular Dependency Detection

**Problem**: Modules depend circularly → hard to test, deploy, understand.

**Why archcheck**: Call graph → directed graph → cycle detection.

```
ALGORITHM:
  1. Build module graph: edge if any call exists
  2. Find Strongly Connected Components (Tarjan): O(V+E)
  3. SCC with |nodes| > 1 = circular dependency

CLASSIFICATION:
  direct:   A → B → A
  indirect: A → B → C → A
  complex:  A → B → C → D → B (nested)

RANKING:
  impact = cycle_size × log(edge_count_in_cycle)

OUTPUT:
  Cycle #1 (CRITICAL, size=3):
    services.auth → services.user → services.permissions → services.auth
    Edges: 47
    Fix: Extract → services.common

  Cycle #2 (WARNING, size=2):
    models.order ↔ models.customer
    Edges: 8
    Fix: Forward reference or mediator

  Cycle #3 (INFO, size=5):
    handlers.* internal
    Note: Same layer, may be acceptable
```

**Data Completeness**: Runtime reveals cycles from dynamic dispatch invisible statically.

**Action**:
- Break cycles via common extraction
- Use dependency injection
- CI gate: no cross-layer cycles

---

## Summary: Philosophy → Capabilities

| # | Use Case | Key Axiom / Feature |
|---|----------|---------------------|
| 1 | Code Path Coverage | Labeling (BOTH vs STATIC_ONLY) |
| 2 | Dynamic Discovery | Data Completeness (RUNTIME_ONLY, VIA_HOF) |
| 3 | Architecture Validation | Uniform Access (by_caller/by_callee) |
| 4 | Type Quality Metrics | Data Completeness (unresolved.reason) |
| 5 | Import Analysis | Data Completeness (all imports) |
| 6 | Test vs Prod | Immutability (safe comparison) |
| 7 | Memory Leak Detection | Data Completeness (traceback) |
| 8 | Sensitive Data Flow | Data Completeness (all args) |
| 9 | Concurrency Bugs | Data Completeness (thread/coro) |
| 10 | Performance Hotspot | Data Completeness (call stack) |
| 11 | Anomaly Detection | No Special Cases (grammar/exception) |
| 12 | Async Task Lifecycle | Data Completeness (task_id, task events) |
| 13 | Code Characteristics | Data Completeness (ρ, ε, ArgsFactory, CR) |
| 14 | Statistical Sampling | Data Completeness (superposition) |
| 15 | **Kinetic Edges** | **IMPOSSIBLE: count(t) time function** |
| 16 | **Multi-Run Comparison** | **IMPOSSIBLE: Confluent merge O(\|G\|)** |
| 17 | **What-If Analysis** | **IMPOSSIBLE: Retroactive Insert/Delete** |
| 18 | **Self-Optimizing** | **MDL Basin Dynamics (no thresholds)** |
| 19 | **Chaotic Code** | **IMPOSSIBLE: Complement Anti-Grammar** |
| 20 | **Succinct Pools** | **IMPOSSIBLE: 2 bits/char PMH** |
| 21 | Coupling & Cohesion | Uniform Access (Ca, Ce, I, IC metrics) |
| 22 | Real Architecture Discovery | Data Completeness (cluster actual calls) |
| 23 | Architecture Drift | Immutability (compare intended vs actual) |
| 24 | Module Role Classification | Uniform Access (fan-in/fan-out patterns) |
| 25 | Dependency Inversion | Data Completeness (DIP score) |
| 26 | Circular Dependencies | Data Completeness (SCC detection) |

---

## Axioms → Capabilities Matrix

```
                        Data     Uniform   Labeling   No Special   Immutable   MDL
                        Complete Access              Cases                    Basin
──────────────────────────────────────────────────────────────────────────────────
Code Path Coverage        ✓                   ✓
Dynamic Discovery         ✓                            ✓
Architecture Valid                  ✓                  ✓
Type Quality              ✓
Import Analysis           ✓
Test vs Prod                                                         ✓
Memory Leak               ✓
Data Flow                 ✓
Concurrency               ✓
Performance               ✓
Anomaly Detection                             ✓        ✓
Async Lifecycle           ✓
Code Characteristics      ✓                                                    ✓
Statistical Sampling      ✓
Kinetic Edges             ✓                                                    ✓
Multi-Run Comparison                                                 ✓
What-If Analysis          ✓
Self-Optimizing           ✓                                                    ✓
Chaotic Code              ✓                            ✓                       ✓
Succinct Pools            ✓                                                    ✓
Coupling & Cohesion       ✓        ✓
Real Architecture         ✓        ✓
Architecture Drift        ✓                                          ✓
Module Roles                       ✓
Dependency Inversion      ✓
Circular Dependencies     ✓
```

---

## What archcheck Does NOT Do

- **Does not define rules** — user specifies patterns
- **Does not make decisions** — provides data
- **Does not hide unresolved** — Data Completeness
- **Does not have built-in layers** — No Special Cases
- **Does not lose data during optimization** — all modes are lossless
