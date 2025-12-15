"""Merge layer for combining AST and Runtime analysis.

Exports:
    - build_merged_graph: Function to merge StaticCallGraph with RuntimeCallGraph
"""

from archcheck.application.merge.builder import build_merged_graph

__all__ = [
    "build_merged_graph",
]
