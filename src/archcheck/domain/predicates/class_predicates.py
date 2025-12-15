"""Class predicates."""

import re
from fnmatch import fnmatch
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.class_ import Class

from archcheck.domain.predicates.base import ClassPredicate


def inherits_from(base: str) -> ClassPredicate:
    """Create predicate: class inherits from base.

    Args:
        base: Base class name or pattern

    Returns:
        Predicate function
    """

    def predicate(cls: Class) -> bool:
        return any(fnmatch(b, base) for b in cls.bases)

    return predicate


def is_decorated_with(decorator: str) -> ClassPredicate:
    """Create predicate: class has decorator.

    Args:
        decorator: Decorator name or pattern

    Returns:
        Predicate function
    """

    def predicate(cls: Class) -> bool:
        return any(fnmatch(d.name, decorator) for d in cls.decorators)

    return predicate


def is_abstract() -> ClassPredicate:
    """Create predicate: class is abstract.

    Returns:
        Predicate function
    """

    def predicate(cls: Class) -> bool:
        return cls.is_abstract

    return predicate


def is_dataclass() -> ClassPredicate:
    """Create predicate: class is dataclass.

    Returns:
        Predicate function
    """

    def predicate(cls: Class) -> bool:
        return cls.is_dataclass

    return predicate


def is_protocol() -> ClassPredicate:
    """Create predicate: class is Protocol.

    Returns:
        Predicate function
    """

    def predicate(cls: Class) -> bool:
        return cls.is_protocol

    return predicate


def is_exception() -> ClassPredicate:
    """Create predicate: class is exception.

    Returns:
        Predicate function
    """

    def predicate(cls: Class) -> bool:
        return cls.is_exception

    return predicate


def has_name_ending_with(suffix: str) -> ClassPredicate:
    """Create predicate: class name ends with suffix.

    Args:
        suffix: Required suffix

    Returns:
        Predicate function
    """

    def predicate(cls: Class) -> bool:
        return cls.name.endswith(suffix)

    return predicate


def has_name_matching(regex: str) -> ClassPredicate:
    """Create predicate: class name matches regex.

    Args:
        regex: Regular expression pattern

    Returns:
        Predicate function

    Raises:
        ValueError: If regex is invalid
    """
    try:
        compiled = re.compile(regex)
    except re.error as e:
        raise ValueError(f"Invalid regex '{regex}': {e}") from e

    def predicate(cls: Class) -> bool:
        return compiled.search(cls.name) is not None

    return predicate
