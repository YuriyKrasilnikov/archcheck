"""Predicate type aliases."""

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.class_ import Class
    from archcheck.domain.model.function import Function
    from archcheck.domain.model.import_ import Import
    from archcheck.domain.model.module import Module

# Type aliases for predicate functions
ModulePredicate = Callable[["Module"], bool]
ClassPredicate = Callable[["Class"], bool]
FunctionPredicate = Callable[["Function"], bool]
ImportPredicate = Callable[["Import"], bool]
