"""Function predicates."""

from fnmatch import fnmatch
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.function import Function

from archcheck.domain.model.enums import Visibility
from archcheck.domain.predicates.base import FunctionPredicate


def is_pure() -> FunctionPredicate:
    """Create predicate: function is pure.

    Returns:
        Predicate function
    """

    def predicate(func: Function) -> bool:
        return func.purity_info is not None and func.purity_info.is_pure

    return predicate


def is_public() -> FunctionPredicate:
    """Create predicate: function is public.

    Returns:
        Predicate function
    """

    def predicate(func: Function) -> bool:
        return func.visibility == Visibility.PUBLIC

    return predicate


def is_private() -> FunctionPredicate:
    """Create predicate: function is private.

    Returns:
        Predicate function
    """

    def predicate(func: Function) -> bool:
        return func.visibility == Visibility.PRIVATE

    return predicate


def is_async() -> FunctionPredicate:
    """Create predicate: function is async.

    Returns:
        Predicate function
    """

    def predicate(func: Function) -> bool:
        return func.is_async

    return predicate


def is_method() -> FunctionPredicate:
    """Create predicate: function is method.

    Returns:
        Predicate function
    """

    def predicate(func: Function) -> bool:
        return func.is_method

    return predicate


def has_decorator(decorator: str) -> FunctionPredicate:
    """Create predicate: function has decorator.

    Args:
        decorator: Decorator name or pattern

    Returns:
        Predicate function
    """

    def predicate(func: Function) -> bool:
        return any(fnmatch(d.name, decorator) for d in func.decorators)

    return predicate


def calls_function(name: str) -> FunctionPredicate:
    """Create predicate: function calls another function.

    Args:
        name: Called function name or pattern

    Returns:
        Predicate function
    """

    def predicate(func: Function) -> bool:
        return any(fnmatch(call_info.callee_name, name) for call_info in func.body_calls)

    return predicate


def has_return_annotation() -> FunctionPredicate:
    """Create predicate: function has return type annotation.

    Returns:
        Predicate function
    """

    def predicate(func: Function) -> bool:
        return func.return_annotation is not None

    return predicate


def has_all_parameters_annotated() -> FunctionPredicate:
    """Create predicate: all parameters have type annotations.

    Returns:
        Predicate function
    """

    def predicate(func: Function) -> bool:
        return all(p.annotation is not None for p in func.parameters)

    return predicate
