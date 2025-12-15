"""Domain predicates."""

from archcheck.domain.predicates.base import (
    ClassPredicate,
    FunctionPredicate,
    ImportPredicate,
    ModulePredicate,
)
from archcheck.domain.predicates.class_predicates import (
    has_name_ending_with,
    has_name_matching,
    inherits_from,
    is_abstract,
    is_dataclass,
    is_decorated_with,
    is_exception,
    is_protocol,
)
from archcheck.domain.predicates.function_predicates import (
    calls_function,
    has_all_parameters_annotated,
    has_decorator,
    has_return_annotation,
    is_async,
    is_method,
    is_private,
    is_public,
    is_pure,
)
from archcheck.domain.predicates.module_predicates import (
    has_import,
    is_in_package,
)
from archcheck.domain.predicates.module_predicates import (
    has_name_matching as module_has_name_matching,
)

__all__ = [
    # Type aliases
    "ModulePredicate",
    "ClassPredicate",
    "FunctionPredicate",
    "ImportPredicate",
    # Module predicates
    "is_in_package",
    "module_has_name_matching",
    "has_import",
    # Class predicates
    "inherits_from",
    "is_decorated_with",
    "is_abstract",
    "is_dataclass",
    "is_protocol",
    "is_exception",
    "has_name_ending_with",
    "has_name_matching",
    # Function predicates
    "is_pure",
    "is_public",
    "is_private",
    "is_async",
    "is_method",
    "has_decorator",
    "calls_function",
    "has_return_annotation",
    "has_all_parameters_annotated",
]
