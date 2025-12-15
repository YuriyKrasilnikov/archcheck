"""Static analysis components for architecture validation.

Exports:
    - StaticCallGraphBuilder: Builds StaticCallGraph from Codebase
    - StaticAnalysisRegistry: Registry of interfaces and implementations
"""

from archcheck.application.static_analysis.graph_builder import StaticCallGraphBuilder
from archcheck.application.static_analysis.registry import StaticAnalysisRegistry

__all__ = [
    "StaticCallGraphBuilder",
    "StaticAnalysisRegistry",
]
