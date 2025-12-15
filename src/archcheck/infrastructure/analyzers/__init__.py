"""AST analyzers for parsing Python code."""

from archcheck.infrastructure.analyzers.base import (
    compute_module_name,
    extract_base_names,
    extract_init_attributes,
    get_docstring,
    get_visibility,
    has_decorator,
    is_generator,
    make_location,
    resolve_relative_import,
    shallow_walk,
    unparse_node,
)
from archcheck.infrastructure.analyzers.body_analyzer import BodyAnalysisResult, BodyAnalyzer
from archcheck.infrastructure.analyzers.class_analyzer import ClassAnalyzer
from archcheck.infrastructure.analyzers.context import AnalysisContext, ContextFrame, ContextType
from archcheck.infrastructure.analyzers.decorator_analyzer import DecoratorAnalyzer
from archcheck.infrastructure.analyzers.function_analyzer import FunctionAnalyzer
from archcheck.infrastructure.analyzers.import_analyzer import ImportAnalyzer

__all__ = [
    # Context
    "AnalysisContext",
    "ContextFrame",
    "ContextType",
    # Base utilities
    "compute_module_name",
    "extract_base_names",
    "extract_init_attributes",
    "get_docstring",
    "get_visibility",
    "has_decorator",
    "is_generator",
    "make_location",
    "resolve_relative_import",
    "shallow_walk",
    "unparse_node",
    # Analyzers
    "BodyAnalyzer",
    "BodyAnalysisResult",
    "ClassAnalyzer",
    "DecoratorAnalyzer",
    "FunctionAnalyzer",
    "ImportAnalyzer",
]
