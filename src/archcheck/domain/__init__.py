"""archcheck domain layer.

Pure domain logic with no external dependencies.
Only imports: typing, abc, dataclasses, enum, pathlib, collections.abc
"""

from archcheck.domain.exceptions import (
    ArchCheckError,
    ArchitectureViolationError,
    ASTError,
    ParsingError,
    RuleValidationError,
)
from archcheck.domain.model import (
    ArchitectureDefinition,
    Class,
    Codebase,
    Component,
    Decorator,
    DIInfo,
    Function,
    Import,
    Layer,
    Location,
    Module,
    Parameter,
    PurityInfo,
    Rule,
    RuleCategory,
    RuleResult,
    Severity,
    Violation,
    Visibility,
)
from archcheck.domain.ports import (
    ReporterPort,
    RuleRepositoryPort,
    SourceParserPort,
)

__all__ = [
    # Exceptions
    "ArchCheckError",
    "ParsingError",
    "ASTError",
    "RuleValidationError",
    "ArchitectureViolationError",
    # Enums
    "Visibility",
    "Severity",
    "RuleCategory",
    # Value objects
    "Location",
    "Decorator",
    "Parameter",
    "PurityInfo",
    "DIInfo",
    # Entities
    "Import",
    "Function",
    "Class",
    "Module",
    "Codebase",
    # Rules
    "Rule",
    "RuleResult",
    "Violation",
    # Architecture
    "Layer",
    "Component",
    "ArchitectureDefinition",
    # Ports
    "SourceParserPort",
    "RuleRepositoryPort",
    "ReporterPort",
]
