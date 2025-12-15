"""Domain ports (interfaces/protocols)."""

# Existing ports
# NEW: Protocols for extensibility
from archcheck.domain.ports.collector import CollectorProtocol
from archcheck.domain.ports.reporter import ReporterPort, ReporterProtocol
from archcheck.domain.ports.rule_repository import RuleRepositoryPort
from archcheck.domain.ports.source_parser import SourceParserPort
from archcheck.domain.ports.validator import ValidatorProtocol
from archcheck.domain.ports.visitor import ViolationDict, VisitorProtocol

__all__ = [
    # Existing ports
    "SourceParserPort",
    "RuleRepositoryPort",
    # Protocols (backwards compat)
    "ReporterPort",
    # NEW: Extensibility protocols
    "VisitorProtocol",
    "ViolationDict",
    "ValidatorProtocol",
    "ReporterProtocol",
    "CollectorProtocol",
]
