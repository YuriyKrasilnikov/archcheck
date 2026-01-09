"""Call resolver: resolve body_calls and decorators to FQN.

Symbol table + import resolution → StaticCallEdge or UnresolvedCall.
Data Completeness: unresolved tracked with reason.
"""

from __future__ import annotations

import builtins
from dataclasses import dataclass
from typing import TYPE_CHECKING

from archcheck.domain.exceptions import ImportLevelExceedsDepthError
from archcheck.domain.static_graph import CallType, StaticCallEdge, UnresolvedCall

if TYPE_CHECKING:
    from archcheck.domain.codebase import Class, Codebase, Function, Import, Module
    from archcheck.domain.events import Location

# Python builtins from stdlib (auto-updated with Python version)
_BUILTINS = frozenset(dir(builtins))

# Call pattern prefixes
_SELF_PREFIX = "self."
_SUPER_PREFIX = "super()."


@dataclass(frozen=True, slots=True)
class _ResolveContext:
    """Context for call resolution within a module."""

    symbol_table: dict[str, str]
    codebase: Codebase
    edges: list[StaticCallEdge]
    unresolved: list[UnresolvedCall]


def resolve_calls(
    module: Module,
    codebase: Codebase,
) -> tuple[tuple[StaticCallEdge, ...], tuple[UnresolvedCall, ...]]:
    """Resolve all calls in module to FQN.

    Processes:
    - Function decorators → DECORATOR edges
    - Function body_calls → DIRECT/CONSTRUCTOR edges
    - Method decorators → DECORATOR edges
    - Method body_calls → METHOD/SUPER/DIRECT/CONSTRUCTOR edges

    Args:
        module: Module with functions, classes, imports.
        codebase: Full codebase for FQN lookup.

    Returns:
        Tuple of (resolved edges, unresolved calls).
    """
    edges: list[StaticCallEdge] = []
    unresolved: list[UnresolvedCall] = []
    ctx = _ResolveContext(
        symbol_table=_build_symbol_table(module),
        codebase=codebase,
        edges=edges,
        unresolved=unresolved,
    )

    # Top-level functions
    for func in module.functions:
        _resolve_function_calls(func, owner_class=None, ctx=ctx)

    # Classes and methods
    for cls in module.classes:
        for method in cls.methods:
            _resolve_function_calls(method, owner_class=cls, ctx=ctx)

    return tuple(edges), tuple(unresolved)


def _build_symbol_table(module: Module) -> dict[str, str]:
    """Build mapping: local_name → FQN.

    Sources:
    - Imports (absolute and relative)
    - Module's own function definitions
    - Module's own class definitions
    """
    symbols: dict[str, str] = {}

    # Imports
    for imp in module.imports:
        local_name, fqn = _resolve_import(imp, module.name)
        symbols[local_name] = fqn

    # Module's own definitions
    for func in module.functions:
        symbols[func.name] = func.qualified_name
    for cls in module.classes:
        symbols[cls.name] = cls.qualified_name

    return symbols


def _resolve_import(imp: Import, module_name: str) -> tuple[str, str]:
    """Resolve import to (local_name, FQN).

    Handles:
    - import X → ("X", "X")
    - import X as Y → ("Y", "X")
    - from X import Y → ("Y", "X.Y")
    - from X import Y as Z → ("Z", "X.Y")
    - from . import Y → ("Y", "<parent>.Y")
    - from ..sub import Y → ("Y", "<grandparent>.sub.Y")
    """
    if imp.is_relative:
        fqn = _resolve_relative_import(imp, module_name)
    elif imp.name is None:
        # import X or import X as Y (whole module)
        fqn = imp.module
    else:
        # from X import Y (specific name)
        fqn = f"{imp.module}.{imp.name}" if imp.module else imp.name

    # Local name: alias > name > module's root
    if imp.alias:
        local_name = imp.alias
    elif imp.name:
        local_name = imp.name
    else:
        # import X.Y.Z → local name is "X"
        local_name = imp.module.partition(".")[0]

    return local_name, fqn


def _resolve_relative_import(imp: Import, module_name: str) -> str:
    """Resolve relative import to absolute FQN.

    Examples:
        module_name="app.services.user", level=1, module="" → "app.services"
        module_name="app.services.user", level=1, module="utils" → "app.services.utils"
        module_name="app.services.user", level=2, module="models" → "app.models"
    """
    parts = module_name.split(".")

    if imp.level > len(parts):
        raise ImportLevelExceedsDepthError(imp.level, len(parts))

    # Go up `level` packages
    parent_parts = parts[: -imp.level] if imp.level > 0 else parts

    # Add submodule if specified
    result_parts = [*parent_parts]
    if imp.module:
        result_parts.append(imp.module)

    # Add imported name if specified
    if imp.name:
        result_parts.append(imp.name)

    return ".".join(result_parts)


def _resolve_function_calls(
    func: Function,
    owner_class: Class | None,
    ctx: _ResolveContext,
) -> None:
    """Resolve calls in function: decorators + body_calls."""
    for dec in func.decorators:
        _resolve_decorator(dec, func.qualified_name, func.location, ctx)

    for call in func.body_calls:
        _resolve_body_call(call, func.qualified_name, owner_class, func.location, ctx)


def _resolve_decorator(
    dec: str,
    caller_fqn: str,
    location: Location,
    ctx: _ResolveContext,
) -> None:
    """Resolve decorator to StaticCallEdge or UnresolvedCall."""
    base_name = _extract_decorator_name(dec)
    _resolve_name_call(base_name, caller_fqn, location, CallType.DECORATOR, ctx)


def _resolve_body_call(
    call_name: str,
    caller_fqn: str,
    owner_class: Class | None,
    location: Location,
    ctx: _ResolveContext,
) -> None:
    """Resolve body call by pattern: self., super()., attr., or simple name."""
    if call_name.startswith(_SELF_PREFIX):
        _resolve_method_call(
            call_name.removeprefix(_SELF_PREFIX),
            caller_fqn,
            owner_class,
            location,
            ctx,
        )
    elif call_name.startswith(_SUPER_PREFIX):
        _resolve_super_call(
            call_name.removeprefix(_SUPER_PREFIX),
            caller_fqn,
            owner_class,
            location,
            ctx,
        )
    elif "." in call_name:
        _resolve_attribute_call(call_name, caller_fqn, location, ctx)
    else:
        _resolve_name_call(call_name, caller_fqn, location, CallType.DIRECT, ctx)


def _extract_decorator_name(dec: str) -> str:
    """Extract base name from decorator: "route('/api')" → "route"."""
    paren_idx = dec.find("(")
    if paren_idx > 0:
        return dec[:paren_idx]
    return dec


def _resolve_method_call(
    method_name: str,
    caller_fqn: str,
    owner_class: Class | None,
    location: Location,
    ctx: _ResolveContext,
) -> None:
    """Resolve self.method() call within class."""
    if owner_class is None:
        ctx.unresolved.append(
            UnresolvedCall(
                caller_fqn=caller_fqn,
                callee_name=f"{_SELF_PREFIX}{method_name}",
                location=location,
                reason="self outside class",
            ),
        )
        return

    # Look for method in owner class
    for method in owner_class.methods:
        if method.name == method_name:
            ctx.edges.append(
                StaticCallEdge(
                    caller_fqn=caller_fqn,
                    callee_fqn=method.qualified_name,
                    location=location,
                    call_type=CallType.METHOD,
                ),
            )
            return

    # Method not found - could be inherited or dynamic
    ctx.unresolved.append(
        UnresolvedCall(
            caller_fqn=caller_fqn,
            callee_name=f"{_SELF_PREFIX}{method_name}",
            location=location,
            reason="method not found",
        ),
    )


def _resolve_super_call(
    method_name: str,
    caller_fqn: str,
    owner_class: Class | None,
    location: Location,
    ctx: _ResolveContext,
) -> None:
    """Resolve super().method() call."""
    if owner_class is None:
        ctx.unresolved.append(
            UnresolvedCall(
                caller_fqn=caller_fqn,
                callee_name=f"{_SUPER_PREFIX}{method_name}",
                location=location,
                reason="super outside class",
            ),
        )
        return

    # Try to find method in parent classes
    for base_name in owner_class.bases:
        parent_fqn = _find_class_fqn(base_name, ctx.symbol_table, ctx.codebase)
        if parent_fqn is None:
            continue

        parent_class = _get_class(parent_fqn, ctx.codebase)
        if parent_class is None:
            continue

        for method in parent_class.methods:
            if method.name == method_name:
                ctx.edges.append(
                    StaticCallEdge(
                        caller_fqn=caller_fqn,
                        callee_fqn=method.qualified_name,
                        location=location,
                        call_type=CallType.SUPER,
                    ),
                )
                return

    # Parent method not found
    ctx.unresolved.append(
        UnresolvedCall(
            caller_fqn=caller_fqn,
            callee_name=f"{_SUPER_PREFIX}{method_name}",
            location=location,
            reason="parent method not found",
        ),
    )


def _resolve_attribute_call(
    call_name: str,
    caller_fqn: str,
    location: Location,
    ctx: _ResolveContext,
) -> None:
    """Resolve obj.method() or module.func() call."""
    match call_name.split(".", 1):
        case [obj_name, attr_name]:
            pass
        case _:
            ctx.unresolved.append(
                UnresolvedCall(
                    caller_fqn=caller_fqn,
                    callee_name=call_name,
                    location=location,
                    reason="invalid call pattern",
                ),
            )
            return

    # Check if obj_name is imported module
    if obj_name not in ctx.symbol_table:
        ctx.unresolved.append(
            UnresolvedCall(
                caller_fqn=caller_fqn,
                callee_name=call_name,
                location=location,
                reason="dynamic",
            ),
        )
        return

    module_fqn = ctx.symbol_table[obj_name]

    # Check if it's a module in codebase
    if module_fqn in ctx.codebase.modules:
        # module.func() pattern
        target_module = ctx.codebase.modules[module_fqn]
        target_fqn = f"{module_fqn}.{attr_name}"

        # Check if function exists
        for func in target_module.functions:
            if func.name == attr_name:
                ctx.edges.append(
                    StaticCallEdge(
                        caller_fqn=caller_fqn,
                        callee_fqn=target_fqn,
                        location=location,
                        call_type=CallType.DIRECT,
                    ),
                )
                return

        # Check if class exists (constructor)
        for cls in target_module.classes:
            if cls.name == attr_name:
                ctx.edges.append(
                    StaticCallEdge(
                        caller_fqn=caller_fqn,
                        callee_fqn=target_fqn,
                        location=location,
                        call_type=CallType.CONSTRUCTOR,
                    ),
                )
                return

        # Not found in module
        ctx.unresolved.append(
            UnresolvedCall(
                caller_fqn=caller_fqn,
                callee_name=call_name,
                location=location,
                reason="not found in module",
            ),
        )
        return

    # obj is not a module - could be instance method call
    ctx.unresolved.append(
        UnresolvedCall(
            caller_fqn=caller_fqn,
            callee_name=call_name,
            location=location,
            reason="dynamic",
        ),
    )


def _resolve_name_call(
    name: str,
    caller_fqn: str,
    location: Location,
    call_type: CallType,
    ctx: _ResolveContext,
) -> None:
    """Resolve simple name call: foo(), Foo()."""
    if name not in ctx.symbol_table:
        reason = "builtin" if name in _BUILTINS else "undefined"
        ctx.unresolved.append(
            UnresolvedCall(
                caller_fqn=caller_fqn,
                callee_name=name,
                location=location,
                reason=reason,
            ),
        )
        return

    fqn = ctx.symbol_table[name]

    # Check if in codebase
    if not _is_in_codebase(fqn, ctx.codebase):
        ctx.unresolved.append(
            UnresolvedCall(
                caller_fqn=caller_fqn,
                callee_name=name,
                location=location,
                reason="external",
            ),
        )
        return

    # Determine actual call type
    actual_type = call_type
    if call_type == CallType.DIRECT and _is_class_fqn(fqn, ctx.codebase):
        actual_type = CallType.CONSTRUCTOR

    ctx.edges.append(
        StaticCallEdge(
            caller_fqn=caller_fqn,
            callee_fqn=fqn,
            location=location,
            call_type=actual_type,
        ),
    )


def _find_class_fqn(
    class_name: str,
    symbol_table: dict[str, str],
    codebase: Codebase,
) -> str | None:
    """Find FQN for class name."""
    # Check symbol table first
    if class_name in symbol_table:
        return symbol_table[class_name]

    # If already qualified
    if "." in class_name:
        return class_name

    # Search all modules (fallback)
    for module in codebase.modules.values():
        for cls in module.classes:
            if cls.name == class_name:
                return cls.qualified_name

    return None


def _get_class(fqn: str, codebase: Codebase) -> Class | None:
    """Get Class by FQN from codebase."""
    match fqn.rsplit(".", 1):
        case [module_name, class_name]:
            pass
        case _:
            return None

    if module_name not in codebase.modules:
        return None

    module = codebase.modules[module_name]
    for cls in module.classes:
        if cls.name == class_name:
            return cls

    return None


def _is_in_codebase(fqn: str, codebase: Codebase) -> bool:
    """Check if FQN exists in codebase (module, class, or function)."""
    # Check module
    if fqn in codebase.modules:
        return True

    # Check class or function: module.name
    match fqn.rsplit(".", 1):
        case [module_name, name]:
            pass
        case _:
            return False

    if module_name not in codebase.modules:
        return False

    module = codebase.modules[module_name]
    return any(f.name == name for f in module.functions) or any(
        c.name == name for c in module.classes
    )


def _is_class_fqn(fqn: str, codebase: Codebase) -> bool:
    """Check if FQN is a class in codebase."""
    match fqn.rsplit(".", 1):
        case [module_name, class_name]:
            pass
        case _:
            return False

    if module_name not in codebase.modules:
        return False

    module = codebase.modules[module_name]
    return any(cls.name == class_name for cls in module.classes)
