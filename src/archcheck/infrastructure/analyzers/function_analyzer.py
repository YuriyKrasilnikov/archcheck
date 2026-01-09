"""Function analyzer: AST → Function domain objects.

Extracts function definition from AST.
Handles: parameters, return type, decorators, body_calls.
"""

from __future__ import annotations

import ast

from archcheck.domain.codebase import Function, Parameter, ParameterKind
from archcheck.domain.events import Location


def analyze_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    module_name: str,
    class_name: str | None = None,
) -> Function:
    """Extract Function from AST node.

    Args:
        node: AST FunctionDef or AsyncFunctionDef node.
        module_name: Fully qualified module name (e.g., "app.service").
        class_name: Class name if method, None if top-level function.

    Returns:
        Function domain object.
    """
    name = node.name
    qualified_name = _build_qualified_name(module_name, class_name, name)

    return Function(
        name=name,
        qualified_name=qualified_name,
        parameters=_extract_parameters(node.args),
        return_annotation=_get_annotation(node.returns),
        location=Location(file=None, line=node.lineno, func=name),
        is_async=isinstance(node, ast.AsyncFunctionDef),
        is_generator=_is_generator(node),
        is_method=class_name is not None,
        decorators=_extract_decorators(node),
        body_calls=_extract_body_calls(node),
    )


def _build_qualified_name(module_name: str, class_name: str | None, func_name: str) -> str:
    """Build fully qualified name for function."""
    if class_name:
        return f"{module_name}.{class_name}.{func_name}"
    return f"{module_name}.{func_name}"


def _extract_parameters(args: ast.arguments) -> tuple[Parameter, ...]:
    """Extract parameters from function arguments."""
    params: list[Parameter] = []

    # Positional-only parameters (before /)
    for arg in args.posonlyargs:
        default = _get_default(args, arg)
        params.append(
            Parameter(
                name=arg.arg,
                annotation=_get_annotation(arg.annotation),
                default=default,
                kind=ParameterKind.POSITIONAL_ONLY,
            ),
        )

    # Regular parameters (between / and *)
    num_defaults = len(args.defaults)
    num_args = len(args.args)
    for i, arg in enumerate(args.args):
        # Defaults are right-aligned
        default_idx = i - (num_args - num_defaults)
        default = ast.unparse(args.defaults[default_idx]) if default_idx >= 0 else None
        params.append(
            Parameter(
                name=arg.arg,
                annotation=_get_annotation(arg.annotation),
                default=default,
                kind=ParameterKind.POSITIONAL_OR_KEYWORD,
            ),
        )

    # *args
    if args.vararg:
        params.append(
            Parameter(
                name=args.vararg.arg,
                annotation=_get_annotation(args.vararg.annotation),
                default=None,
                kind=ParameterKind.VAR_POSITIONAL,
            ),
        )

    # Keyword-only parameters (after *)
    for i, arg in enumerate(args.kwonlyargs):
        kw_default = args.kw_defaults[i]
        default = ast.unparse(kw_default) if kw_default is not None else None
        params.append(
            Parameter(
                name=arg.arg,
                annotation=_get_annotation(arg.annotation),
                default=default,
                kind=ParameterKind.KEYWORD_ONLY,
            ),
        )

    # **kwargs
    if args.kwarg:
        params.append(
            Parameter(
                name=args.kwarg.arg,
                annotation=_get_annotation(args.kwarg.annotation),
                default=None,
                kind=ParameterKind.VAR_KEYWORD,
            ),
        )

    return tuple(params)


def _get_default(args: ast.arguments, arg: ast.arg) -> str | None:
    """Get default value for positional-only parameter."""
    # Positional-only defaults are in args.defaults, right-aligned with posonlyargs + args
    all_pos = args.posonlyargs + args.args
    try:
        idx = all_pos.index(arg)
    except ValueError:
        return None

    num_defaults = len(args.defaults)
    num_all = len(all_pos)
    default_idx = idx - (num_all - num_defaults)

    if default_idx >= 0:
        return ast.unparse(args.defaults[default_idx])
    return None


def _get_annotation(node: ast.expr | None) -> str | None:
    """Convert annotation AST to string."""
    if node is None:
        return None
    return ast.unparse(node)


def _is_generator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if function contains yield/yield from."""
    return any(isinstance(child, (ast.Yield, ast.YieldFrom)) for child in ast.walk(node))


def _extract_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    """Extract decorator names."""
    return tuple(ast.unparse(dec) for dec in node.decorator_list)


def _extract_body_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    """Extract unresolved call names from function body.

    Returns raw call expressions as strings.
    Resolution to FQN happens in call_resolver.
    """
    calls: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            call_str = _get_call_name(child.func)
            if call_str:
                calls.append(call_str)
    return tuple(calls)


def _get_call_name(node: ast.expr) -> str | None:
    """Get call target name as string."""
    match node:
        case ast.Name():
            return node.id
        case ast.Attribute():
            return ast.unparse(node)
        case _:
            return None
