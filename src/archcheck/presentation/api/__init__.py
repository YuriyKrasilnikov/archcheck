"""Fluent API for architecture testing.

Public exports:
    ArchCheck: Entry point for fluent DSL
    ModuleQuery/ModuleAssertion: Module query and assertion builders
    ClassQuery/ClassAssertion: Class query and assertion builders
    FunctionQuery/FunctionAssertion: Function query and assertion builders
    EdgeQuery/EdgeAssertion: Edge query and assertion builders
    compile_pattern: Pattern compilation
    CompiledPattern: Compiled pattern type
"""

from archcheck.presentation.api.dsl import (
    ArchCheck,
    ClassAssertion,
    ClassQuery,
    EdgeAssertion,
    EdgeQuery,
    FunctionAssertion,
    FunctionQuery,
    ModuleAssertion,
    ModuleQuery,
)
from archcheck.presentation.api.patterns import (
    CompiledPattern,
    compile_pattern,
)

__all__ = [
    "ArchCheck",
    "ClassAssertion",
    "ClassQuery",
    "CompiledPattern",
    "EdgeAssertion",
    "EdgeQuery",
    "FunctionAssertion",
    "FunctionQuery",
    "ModuleAssertion",
    "ModuleQuery",
    "compile_pattern",
]
