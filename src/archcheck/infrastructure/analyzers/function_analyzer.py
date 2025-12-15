"""Function/method analyzer."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from archcheck.domain.model.function import Function
from archcheck.domain.model.parameter import Parameter
from archcheck.infrastructure.analyzers.base import (
    get_visibility,
    has_decorator,
    is_generator,
    make_location,
    unparse_node,
)
from archcheck.infrastructure.analyzers.body_analyzer import BodyAnalyzer
from archcheck.infrastructure.analyzers.decorator_analyzer import DecoratorAnalyzer

if TYPE_CHECKING:
    from pathlib import Path

    from archcheck.domain.model.symbol_table import SymbolTable


class FunctionAnalyzer:
    """Extracts function/method information from Python AST.

    Stateless analyzer - no state between analyze() calls.
    """

    def __init__(self) -> None:
        self._decorator_analyzer = DecoratorAnalyzer()
        self._body_analyzer = BodyAnalyzer()

    def analyze(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        path: Path,
        module_name: str,
        class_name: str | None = None,
        symbol_table: SymbolTable | None = None,
        known_classes: frozenset[str] | None = None,
    ) -> Function:
        """Analyze function/method AST node.

        Args:
            node: Function or AsyncFunctionDef AST node
            path: Source file path
            module_name: Fully qualified module name
            class_name: Enclosing class name (None for module-level functions)
            symbol_table: Symbol table for name resolution
            known_classes: Known class names in module for CONSTRUCTOR detection

        Returns:
            Function object

        Raises:
            TypeError: If required parameters are None (FAIL-FIRST)
            ValueError: If module_name is empty (FAIL-FIRST)
        """
        # FAIL-FIRST: validate required parameters
        if node is None:
            raise TypeError("node must not be None")
        if path is None:
            raise TypeError("path must not be None")
        if not module_name:
            raise ValueError("module_name must be non-empty string")

        name = node.name
        is_method = class_name is not None

        # Build qualified name
        if class_name:
            qualified_name = f"{module_name}.{class_name}.{name}"
        else:
            qualified_name = f"{module_name}.{name}"

        # Analyze decorators
        decorators = self._decorator_analyzer.analyze(node.decorator_list, path)

        # Check for special method types
        is_classmethod = has_decorator(node.decorator_list, "classmethod")
        is_staticmethod = has_decorator(node.decorator_list, "staticmethod")
        is_property = has_decorator(node.decorator_list, "property")
        is_abstract = has_decorator(node.decorator_list, "abstractmethod")

        # Extract parameters
        parameters = self._extract_parameters(node.args)

        # Get return annotation
        return_annotation: str | None = None
        if node.returns:
            return_annotation = unparse_node(node.returns)

        # Analyze body
        param_names = frozenset(p.name for p in parameters)
        body_result = self._body_analyzer.analyze(
            node.body,
            param_names,
            symbol_table,
            known_classes,
        )

        return Function(
            name=name,
            qualified_name=qualified_name,
            parameters=parameters,
            return_annotation=return_annotation,
            decorators=decorators,
            location=make_location(node, path),
            visibility=get_visibility(name),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_generator=is_generator(node),
            is_method=is_method,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            is_property=is_property,
            is_abstract=is_abstract,
            purity_info=None,  # Purity analysis is separate concern
            body_calls=body_result.calls,
            body_attributes=body_result.attributes,
            body_globals_read=body_result.globals_read,
            body_globals_write=body_result.globals_write,
        )

    def _extract_parameters(self, args: ast.arguments) -> tuple[Parameter, ...]:
        """Extract parameters from function arguments.

        Args:
            args: Function arguments AST node

        Returns:
            Tuple of Parameter objects
        """
        params: list[Parameter] = []

        # Positional-only parameters (before /)
        posonlyargs = args.posonlyargs
        num_posonly = len(posonlyargs)

        # Regular parameters (positional-or-keyword)
        regular_args = args.args

        # Keyword-only parameters (after *)
        kwonlyargs = args.kwonlyargs

        # Defaults: right-aligned to args
        # If we have 3 args and 2 defaults, first arg has no default
        defaults = args.defaults
        num_regular = len(regular_args)
        num_defaults = len(defaults)

        # kw_defaults: aligned 1:1 with kwonlyargs, None if no default
        kw_defaults = args.kw_defaults

        # Process positional-only parameters
        # Defaults are right-aligned across ALL positional params (posonly + regular)
        total_positional = num_posonly + num_regular
        first_with_default = total_positional - num_defaults

        for i, arg in enumerate(posonlyargs):
            default: str | None = None
            if i >= first_with_default:
                default_idx = i - first_with_default
                default = unparse_node(defaults[default_idx])

            params.append(
                Parameter(
                    name=arg.arg,
                    annotation=unparse_node(arg.annotation) if arg.annotation else None,
                    default=default,
                    is_positional_only=True,
                )
            )

        # Process regular parameters
        # Continue counting from where posonly left off
        for i, arg in enumerate(regular_args):
            default = None
            global_idx = num_posonly + i
            if global_idx >= first_with_default:
                default_idx = global_idx - first_with_default
                default = unparse_node(defaults[default_idx])

            params.append(
                Parameter(
                    name=arg.arg,
                    annotation=unparse_node(arg.annotation) if arg.annotation else None,
                    default=default,
                )
            )

        # Process *args
        if args.vararg:
            vararg_ann = args.vararg.annotation
            params.append(
                Parameter(
                    name=args.vararg.arg,
                    annotation=unparse_node(vararg_ann) if vararg_ann else None,
                    is_variadic=True,
                )
            )

        # Process keyword-only parameters
        for i, arg in enumerate(kwonlyargs):
            default = None
            kw_default = kw_defaults[i]
            if kw_default is not None:
                default = unparse_node(kw_default)

            params.append(
                Parameter(
                    name=arg.arg,
                    annotation=unparse_node(arg.annotation) if arg.annotation else None,
                    default=default,
                    is_keyword_only=True,
                )
            )

        # Process **kwargs
        if args.kwarg:
            kwarg_ann = args.kwarg.annotation
            params.append(
                Parameter(
                    name=args.kwarg.arg,
                    annotation=unparse_node(kwarg_ann) if kwarg_ann else None,
                    is_variadic_keyword=True,
                )
            )

        return tuple(params)
