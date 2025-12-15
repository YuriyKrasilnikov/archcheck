"""Domain exceptions."""

from archcheck.domain.exceptions.base import ArchCheckError
from archcheck.domain.exceptions.parsing import ASTError, ParsingError
from archcheck.domain.exceptions.validation import RuleValidationError
from archcheck.domain.exceptions.violation import ArchitectureViolationError

__all__ = [
    "ArchCheckError",
    "ParsingError",
    "ASTError",
    "RuleValidationError",
    "ArchitectureViolationError",
]
