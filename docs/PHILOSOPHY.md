# archcheck Design Philosophy

## Core Principle

**User configuration = source of truth. Code = execution engine.**

```
WRONG:  Library defines behavior, user can tweak
RIGHT:  User defines behavior, library provides defaults as convenience
```

---

## Design Axioms

### 1. No Special Cases

```
WRONG:
    Built-in categories: request, test, startup (special)
    Custom categories: user-defined (second-class)

RIGHT:
    All categories: user-defined strings
    DEFAULT_ENTRY_PATTERNS: just config data, same status as user config
```

**Test:** Can user completely replace any default with their own? If no → redesign.

---

### 2. Configuration Over Code

```
WRONG:
    class BuiltinEntryCategory(Enum):
        REQUEST = "request"  # hardcoded in library

RIGHT:
    DEFAULT_ENTRY_PATTERNS = {"request": ("*_handler",)}  # config data
    # User can ignore, override, extend
```

**Test:** Is behavior defined by data or by code? If code → extract to config.

---

### 3. Uniform Access

```
WRONG:
    categories.request        # special property for built-in
    categories.custom["cron"] # different API for user-defined

RIGHT:
    categories["request"]     # same API
    categories["cron"]        # same API
```

**Test:** Does API differ based on who defined the data? If yes → unify.

---

### 4. Data Completeness

```
WRONG:
    Entry points not matching patterns → lost

RIGHT:
    Entry points not matching patterns → tracked in .uncategorized
    Invariant: all_entry_points = categorized ∪ uncategorized
```

**Test:** Can user recover all input data from output? If no → add tracking.

---

### 5. Labeling Over Partitioning

```
WRONG (partitioning):
    Every item MUST belong to exactly one category
    OTHER = forced fallback bucket

RIGHT (labeling):
    Items matching patterns → labeled
    Items not matching → unlabeled (separate tracking)
    User decides if they want catch-all pattern
```

**Test:** Is there a forced "other" category? If yes → make it optional.

---

### 6. Order = Priority (When Order Matters)

```
patterns = {
    "test": ("test_*",),      # checked first
    "request": ("get_*",),    # checked second
}

# "test_get_handler" → matches "test" (first wins)
```

**Test:** Is priority implicit (hardcoded) or explicit (user-controlled)? If implicit → make explicit via order.

---

### 7. FAIL-FIRST Validation

```
WRONG:
    if not valid:
        use_default()  # silent fallback

RIGHT:
    if not valid:
        raise InvalidPatternError(...)  # immediate failure
```

**Test:** Does invalid input silently degrade? If yes → make it fail.

---

### 8. Immutability

```
WRONG:
    categories["test"] = new_value  # mutable

RIGHT:
    categories = EntryPointCategories(...)  # immutable
    # Modifications create new instances
```

**Test:** Can state be modified after creation? If yes → freeze.

---

## Feature Design Checklist

When designing any feature, verify:

| Check | Question |
|-------|----------|
| No Special Cases | Can user replace ALL defaults? |
| Config Over Code | Is behavior defined by data, not code? |
| Uniform Access | Is API identical for all cases? |
| Data Completeness | Can user recover all input from output? |
| Labeling Over Partitioning | Is "uncategorized" optional, not forced? |
| Order = Priority | Is priority explicit via config order? |
| FAIL-FIRST | Does invalid input fail immediately? |
| Immutability | Is result frozen after creation? |

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  APPLICATION                                                    │
│      constants.py → DEFAULT_* configs (just data)               │
│      services    → orchestration                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  INFRASTRUCTURE                                                 │
│      Classifiers, Analyzers → stateless, config-driven          │
│      Input: user config or defaults                             │
│      Output: domain objects                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  DOMAIN                                                         │
│      Models → immutable value objects                           │
│      No behavior assumptions                                    │
│      Data containers with invariant validation                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example: Entry Point Categorization

### Wrong Design (Rejected)

```
class BuiltinEntryCategory(Enum):
    REQUEST = "request"
    TEST = "test"
    OTHER = "other"  # forced fallback

class EntryPointCategories:
    request: frozenset[str]  # special field
    test: frozenset[str]     # special field
    other: frozenset[str]    # forced catchall
    custom: dict[str, frozenset[str]]  # second-class
```

Problems:
- Built-in categories are special (enum)
- OTHER is forced (partitioning)
- Two different APIs (properties vs dict)

### Right Design (Implemented)

```
DEFAULT_ENTRY_PATTERNS = {
    "test": ("test_*",),
    "request": ("*_handler",),
}  # Just config data

class EntryPointCategories(Mapping[str, frozenset[str]]):
    _categorized: Mapping[str, frozenset[str]]
    _uncategorized: frozenset[str]

    # Uniform access: categories["test"], categories["cron"]
    # Uncategorized: separate, not a category
```

Benefits:
- All categories equal (just strings)
- User controls everything via patterns config
- Unified API
- Uncategorized is optional tracking, not forced bucket

---

## Example: Code Extensibility (Strategies)

### Wrong Design (Rejected)

```
Engine contains switch over built-in types.
User-defined → fallback branch with limited behavior.
New type → engine modification required.
```

Problems:
- Built-in ≠ user-defined (special cases)
- Closed for extension

### Right Design (Implemented)

```
Single ABC. All implement identically.
Engine calls ABC method, unaware of concrete types.
Built-in = implemented as user would.
```

```
WRONG:                              RIGHT:

Engine                              Engine
  │                                   │
  ├─→ BuiltinA (special)              └─→ ABC.method()
  ├─→ BuiltinB (special)                    ↑
  └─→ default (user)                   ┌────┴────┐
                                    BuiltinA  UserX
                                   (same ABC) (same ABC)
```

Benefits:
- User can implement equivalent of any built-in via same ABC
- New strategy = new class, no engine changes
- Open/Closed principle

---

## Anti-Patterns

| Anti-Pattern | Why Wrong | Fix |
|--------------|-----------|-----|
| `BuiltinX` enum | Creates special cases | Use plain strings |
| `.request` property | Special access for built-in | Uniform `["request"]` |
| `OTHER` category | Forced fallback | Separate `.uncategorized` |
| Hardcoded defaults in code | Can't be fully replaced | Move to config constant |
| Silent fallback on error | Hides bugs | FAIL-FIRST exception |
| Mutable result | Unpredictable state | Immutable dataclass |

---

## Summary

**archcheck = user-extensible architecture validation**

Every feature must be:
1. **Fully configurable** by user
2. **Uniform** in API regardless of who defined the data
3. **Complete** in tracking all input data
4. **Explicit** in behavior (no hidden defaults)
5. **Immutable** in results
6. **Fail-fast** on invalid input

Defaults exist for convenience, not as special cases.
