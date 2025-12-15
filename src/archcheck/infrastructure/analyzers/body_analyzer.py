"""Function body analyzer using two-phase approach.

Phase 1: Collect all locally bound names
Phase 2: Classify Name usages as local or global

This separation ensures correct scoping analysis regardless of AST traversal order.
"""

from __future__ import annotations

import ast
import builtins
from dataclasses import dataclass
from typing import TYPE_CHECKING

from archcheck.domain.model.call_info import CallInfo
from archcheck.domain.model.call_type import CallType
from archcheck.infrastructure.analyzers.base import shallow_walk

if TYPE_CHECKING:
    from archcheck.domain.model.symbol_table import SymbolTable


@dataclass(frozen=True, slots=True)
class BodyAnalysisResult:
    """Result of function body analysis.

    Attributes:
        calls: Function/method calls in body (with full info)
        attributes: Attribute accesses (self.x, obj.y)
        globals_read: Global variables read
        globals_write: Global variables written
    """

    calls: tuple[CallInfo, ...]
    attributes: frozenset[str]
    globals_read: frozenset[str]
    globals_write: frozenset[str]


class BodyAnalyzer:
    """Analyzes function body for calls, attributes, globals.

    Uses two-phase analysis for correct scoping:
    1. Collect ALL locally bound names first
    2. Classify Name usages knowing what's local

    Stateless - no state between analyze() calls.
    Does NOT enter nested functions/classes - they have own scope.
    """

    def analyze(
        self,
        body: list[ast.stmt],
        local_names: frozenset[str] | None = None,
        symbol_table: SymbolTable | None = None,
        known_classes: frozenset[str] | None = None,
    ) -> BodyAnalysisResult:
        """Analyze function body statements.

        Args:
            body: List of body statements
            local_names: Known local variable names (parameters)
            symbol_table: Symbol table for name resolution (optional)
            known_classes: Known class names in current module for CONSTRUCTOR detection

        Returns:
            BodyAnalysisResult with extracted information
        """
        # Phase 1: Collect all names bound in this scope
        bound_names, global_decls = _collect_bindings(body)

        # Combine with parameters, exclude global declarations
        all_locals = ((local_names or frozenset()) | bound_names) - global_decls

        # Phase 2: Classify usages with complete local knowledge
        return _classify_usages(
            body,
            all_locals,
            global_decls,
            symbol_table,
            known_classes or frozenset(),
        )


# =============================================================================
# PHASE 1: Collect bound names
# =============================================================================


def _collect_bindings(body: list[ast.stmt]) -> tuple[frozenset[str], frozenset[str]]:
    """Collect all names bound in this scope.

    Returns:
        Tuple of (bound_names, global_declarations)

    Bound names include:
    - Assignment targets (Assign, AnnAssign)
    - For/AsyncFor loop targets
    - With/AsyncWith targets
    - ExceptHandler names
    - NamedExpr (walrus) targets
    - Comprehension variables
    - Nested function/class names
    - Import names

    NOT included:
    - AugAssign targets (x += 1 requires x to exist)
    - global declarations (they make name global, not local)
    """
    bound: set[str] = set()
    global_decls: set[str] = set()

    for node in shallow_walk(body):
        match node:
            # === Global declarations (special - excludes from local) ===
            case ast.Global(names=names):
                global_decls.update(names)

            # === Assignments ===
            case ast.Assign(targets=targets):
                for target in targets:
                    _extract_target_names(target, bound)

            case ast.AnnAssign(target=target):
                _extract_target_names(target, bound)

            # NOTE: AugAssign (x += 1) does NOT create binding!
            # It requires x to already exist.

            # === Control flow with targets ===
            case ast.For(target=target) | ast.AsyncFor(target=target):
                _extract_target_names(target, bound)

            case ast.With(items=items) | ast.AsyncWith(items=items):
                for item in items:
                    if item.optional_vars:
                        _extract_target_names(item.optional_vars, bound)

            case ast.ExceptHandler(name=name) if name is not None:
                bound.add(name)

            # === Walrus operator ===
            case ast.NamedExpr(target=ast.Name(id=name)):
                bound.add(name)

            # === Comprehensions ===
            # ast.comprehension is yielded as child node by shallow_walk.
            # We handle it here - no need to duplicate in ListComp/SetComp/etc.
            # Note: In Python 3, comprehension variables do NOT leak to parent scope.
            # We track them to prevent false positives in globals detection.
            case ast.comprehension(target=target):
                _extract_target_names(target, bound)

            # === Nested scopes (name itself is bound in parent) ===
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name):
                bound.add(name)

            case ast.ClassDef(name=name):
                bound.add(name)

            # === Imports (create local binding) ===
            case ast.Import(names=aliases):
                for alias in aliases:
                    name = alias.asname if alias.asname else alias.name.split(".")[0]
                    bound.add(name)

            case ast.ImportFrom(names=aliases):
                for alias in aliases:
                    name = alias.asname if alias.asname else alias.name
                    bound.add(name)

    return frozenset(bound), frozenset(global_decls)


def _extract_target_names(target: ast.expr, names: set[str]) -> None:
    """Extract variable names from assignment target.

    Handles:
    - Simple: x = ...
    - Tuple/List: a, b = ... or [a, b] = ...
    - Starred: *rest = ...

    Does NOT extract from:
    - Attribute: obj.x = ... (doesn't bind name)
    - Subscript: arr[0] = ... (doesn't bind name)
    """
    match target:
        case ast.Name(id=name):
            names.add(name)
        case ast.Tuple(elts=elts) | ast.List(elts=elts):
            for elt in elts:
                _extract_target_names(elt, names)
        case ast.Starred(value=value):
            _extract_target_names(value, names)
        # ast.Attribute and ast.Subscript don't create bindings


# =============================================================================
# PHASE 2: Classify usages
# =============================================================================


def _classify_usages(
    body: list[ast.stmt],
    all_locals: frozenset[str],
    global_decls: frozenset[str],
    symbol_table: SymbolTable | None,
    known_classes: frozenset[str],
) -> BodyAnalysisResult:
    """Classify Name usages knowing all locals.

    Args:
        body: Function body statements
        all_locals: All locally bound names (params + assignments)
        global_decls: Names declared with `global` statement
        symbol_table: Symbol table for name resolution
        known_classes: Known class names for CONSTRUCTOR detection

    Returns:
        BodyAnalysisResult with classified information
    """
    calls: list[CallInfo] = []
    attributes: set[str] = set()
    globals_read: set[str] = set()
    globals_write: set[str] = set()

    for node in shallow_walk(body):
        match node:
            # === Calls ===
            case ast.Call(func=func):
                call_info = _extract_call_info(func, node.lineno, symbol_table, known_classes)
                if call_info is not None:
                    calls.append(call_info)

            # === Attribute access ===
            case ast.Attribute():
                attributes.add(ast.unparse(node))

            # === Name reads ===
            case ast.Name(id=name, ctx=ast.Load()):
                if _is_global_name(name, all_locals):
                    globals_read.add(name)

            # === Name writes ===
            # Note: ast.Name(ctx=Store) is NOT handled here for globals_write.
            # In Python, assignment without `global` creates LOCAL variable.
            # Global writes only happen via:
            # 1. `global x` declaration (handled by ast.Global case)
            # 2. `del x` where x is not local (handled below)
            # 3. `x += 1` where x is not local (handled by ast.AugAssign case)

            case ast.Name(id=name, ctx=ast.Del()):
                if _is_global_name(name, all_locals):
                    globals_write.add(name)

            # === AugAssign (read + write) ===
            case ast.AugAssign(target=ast.Name(id=name)):
                if _is_global_name(name, all_locals):
                    globals_read.add(name)
                    globals_write.add(name)

            # === Global declarations always tracked ===
            case ast.Global(names=names):
                for name in names:
                    globals_write.add(name)

    return BodyAnalysisResult(
        calls=tuple(calls),
        attributes=frozenset(attributes),
        globals_read=frozenset(globals_read),
        globals_write=frozenset(globals_write),
    )


# =============================================================================
# CALL INFO EXTRACTION
# =============================================================================


def _extract_call_info(
    func: ast.expr,
    line: int,
    symbol_table: SymbolTable | None,
    known_classes: frozenset[str],
) -> CallInfo | None:
    """Extract CallInfo from function expression.

    Handles:
    - func() → FUNCTION or CONSTRUCTOR
    - obj.method() → METHOD
    - self.method() → METHOD
    - super().method() → SUPER
    - Module.func() → FUNCTION
    - Class() → CONSTRUCTOR

    Args:
        func: Function expression from ast.Call
        line: Line number of the call
        symbol_table: Symbol table for resolution
        known_classes: Known class names for CONSTRUCTOR detection

    Returns:
        CallInfo or None if cannot extract
    """
    match func:
        # Simple name call: func() or MyClass()
        case ast.Name(id=name):
            call_type = _determine_call_type_for_name(name, known_classes)
            resolved = _resolve_name(name, symbol_table)
            return CallInfo(
                callee_name=name,
                resolved_fqn=resolved,
                line=line,
                call_type=call_type,
            )

        # Method or attribute call: obj.method() or self.method() or super().method()
        case ast.Attribute(value=value, attr=attr):
            callee_name = ast.unparse(func)
            call_type = _determine_call_type_for_attribute(value, attr, known_classes)

            # Try to resolve
            resolved = None
            if symbol_table is not None:
                resolved = symbol_table.resolve(callee_name)

            return CallInfo(
                callee_name=callee_name,
                resolved_fqn=resolved,
                line=line,
                call_type=call_type,
            )

        # Chained call: factory()() or get_handler()()
        case ast.Call(func=inner_func):
            inner_name = _get_simple_name(inner_func)
            if inner_name is not None:
                callee_name = f"{inner_name}()"
                return CallInfo(
                    callee_name=callee_name,
                    resolved_fqn=None,  # Cannot resolve chained calls
                    line=line,
                    call_type=CallType.FUNCTION,
                )
            return None

        # Subscript call: arr[0]() or handlers["key"]()
        case ast.Subscript():
            callee_name = ast.unparse(func)
            return CallInfo(
                callee_name=callee_name,
                resolved_fqn=None,  # Cannot resolve subscript calls
                line=line,
                call_type=CallType.FUNCTION,
            )

    return None


def _determine_call_type_for_name(
    name: str,
    known_classes: frozenset[str],
) -> CallType:
    """Determine CallType for simple name.

    Args:
        name: Function/class name
        known_classes: Known class names in scope

    Returns:
        CONSTRUCTOR if name is known class or CamelCase, else FUNCTION
    """
    # Exact match in known classes
    if name in known_classes:
        return CallType.CONSTRUCTOR

    # Heuristic: CamelCase names are likely constructors
    # This handles imported classes not in known_classes
    if _is_camel_case(name):
        return CallType.CONSTRUCTOR

    return CallType.FUNCTION


def _determine_call_type_for_attribute(
    value: ast.expr,
    attr: str,
    known_classes: frozenset[str],
) -> CallType:
    """Determine CallType for attribute access.

    Args:
        value: Object being accessed
        attr: Attribute/method name
        known_classes: Known class names

    Returns:
        CallType based on pattern
    """
    match value:
        # self.method() → METHOD
        case ast.Name(id="self"):
            return CallType.METHOD

        # cls.method() → METHOD (classmethod)
        case ast.Name(id="cls"):
            return CallType.METHOD

        # super().method() → SUPER
        case ast.Call(func=ast.Name(id="super")):
            return CallType.SUPER

        # Module.Class() → CONSTRUCTOR
        case ast.Name():
            if _is_camel_case(attr):
                return CallType.CONSTRUCTOR
            # Module.function() is still METHOD-like access
            return CallType.METHOD

        # Nested attribute: a.b.method()
        case ast.Attribute():
            if _is_camel_case(attr):
                return CallType.CONSTRUCTOR
            return CallType.METHOD

    # Default to METHOD for any other attribute access
    return CallType.METHOD


def _resolve_name(
    name: str,
    symbol_table: SymbolTable | None,
) -> str | None:
    """Resolve name using symbol table.

    Args:
        name: Name to resolve
        symbol_table: Symbol table (may be None)

    Returns:
        Resolved FQN or None
    """
    if symbol_table is None:
        return None
    return symbol_table.resolve(name)


def _get_simple_name(node: ast.expr) -> str | None:
    """Get simple name from expression.

    Args:
        node: AST expression

    Returns:
        Simple name or None
    """
    match node:
        case ast.Name(id=name):
            return name
        case ast.Attribute(attr=attr):
            return attr
    return None


def _is_camel_case(name: str) -> bool:
    """Check if name is CamelCase (likely a class).

    Args:
        name: Name to check

    Returns:
        True if CamelCase pattern
    """
    # Must start with uppercase
    if not name or not name[0].isupper():
        return False

    # Must have at least one lowercase (to distinguish from CONSTANTS)
    has_lower = any(c.islower() for c in name)

    # Must not be all uppercase (CONSTANT)
    is_all_upper = name.isupper()

    return has_lower and not is_all_upper


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _is_builtin(name: str) -> bool:
    """Check if name is a Python builtin."""
    return name in _BUILTINS


def _is_global_name(name: str, all_locals: frozenset[str]) -> bool:
    """Check if name should be tracked as global.

    A name is global if:
    1. It's not in the local scope (parameters + assignments)
    2. It's not a Python builtin

    This is the single source of truth for global name detection.
    """
    return name not in all_locals and not _is_builtin(name)


# =============================================================================
# BUILTINS - Discovered via dir(builtins), NOT hardcoded
# =============================================================================

# Python builtins - discover dynamically (includes functions, exceptions, constants)
_PYTHON_BUILTINS = frozenset(dir(builtins))

# Type hints NOT in builtins - minimal explicit set
# These are typing module exports that appear as bare names in type annotations
_TYPE_HINT_NAMES = frozenset(
    {
        # Core typing constructs
        "Any",
        "Callable",
        "Optional",
        "Union",
        "List",
        "Dict",
        "Set",
        "Tuple",
        "Type",
        "Generic",
        "Protocol",
        "Final",
        "Literal",
        "TypeVar",
        "Self",
        "Never",
        "TypeAlias",
        "ClassVar",
        "Annotated",
        "TypedDict",
        # Collection ABCs commonly used as type hints
        "Sequence",
        "Mapping",
        "Iterable",
        "Iterator",
        "MutableSequence",
        "MutableMapping",
        "MutableSet",
        "Awaitable",
        "Coroutine",
        "AsyncIterator",
        "AsyncIterable",
        "Generator",
        "AsyncGenerator",
        # Python 3.14+ type parameter syntax support
        "TypeVarTuple",
        "ParamSpec",
        "Concatenate",
        "Unpack",
    }
)

# Combined builtins - all names that should not be tracked as "globals"
_BUILTINS = _PYTHON_BUILTINS | _TYPE_HINT_NAMES
