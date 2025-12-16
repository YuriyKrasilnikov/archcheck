"""Merge layer for combining AST and Runtime analysis.

Exports:
    - build_merged_graph: Merge StaticCallGraph with RuntimeCallGraph
    - build_static_merged_graph: Build MergedCallGraph from static only
"""

from archcheck.application.merge.builder import (
    build_merged_graph,
    build_static_merged_graph,
)

__all__ = [
    "build_merged_graph",
    "build_static_merged_graph",
]
