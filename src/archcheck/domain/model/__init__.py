"""Domain model entities."""

# Architecture
from archcheck.domain.model.architecture import (
    ArchitectureDefinition,
    ArchitectureDefinitionBuilder,
    Component,
    Layer,
)
from archcheck.domain.model.async_call_graph import AsyncCallGraph

# Existing graphs
from archcheck.domain.model.call_graph import CallGraph

# NEW: Edge types (Edge Architecture)
from archcheck.domain.model.call_instance import CallInstance

# NEW: Runtime types (Python 3.14)
from archcheck.domain.model.call_site import CallSite

# NEW: Static analysis types
from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.callee_info import CalleeInfo
from archcheck.domain.model.callee_kind import CalleeKind

# NEW: Validation types
from archcheck.domain.model.check_result import CheckResult
from archcheck.domain.model.check_stats import CheckStats
from archcheck.domain.model.class_ import Class
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.combined_call_graph import CombinedCallGraph

# NEW: Configuration
from archcheck.domain.model.configuration import ArchitectureConfig
from archcheck.domain.model.coverage_report import CoverageReport
from archcheck.domain.model.decorator import Decorator
from archcheck.domain.model.di import DIInfo
from archcheck.domain.model.edge_nature import EdgeNature

# NEW: Merged types
from archcheck.domain.model.entry_points import EntryPointCategories
from archcheck.domain.model.enums import RuleCategory, Severity, Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.function_edge import FunctionEdge
from archcheck.domain.model.function_info import FunctionInfo
from archcheck.domain.model.graph import DiGraph, detect_cycles, topological_order
from archcheck.domain.model.hidden_dep import HiddenDep, HiddenDepType
from archcheck.domain.model.implementation_info import ImplementationInfo
from archcheck.domain.model.import_ import Import
from archcheck.domain.model.import_graph import ImportGraph
from archcheck.domain.model.inheritance_graph import InheritanceGraph
from archcheck.domain.model.interface_info import InterfaceInfo
from archcheck.domain.model.layer_violation import LayerViolation
from archcheck.domain.model.lib_call_site import LibCallSite
from archcheck.domain.model.lib_edge import LibEdge
from archcheck.domain.model.location import Location
from archcheck.domain.model.merged_call_graph import MergedCallGraph
from archcheck.domain.model.module import Module
from archcheck.domain.model.parameter import Parameter
from archcheck.domain.model.purity import PurityInfo
from archcheck.domain.model.rule import Rule, RuleResult
from archcheck.domain.model.runtime_call_graph import (
    FrozenRuntimeCallGraph,
    RuntimeCallGraph,
)
from archcheck.domain.model.static_call_edge import StaticCallEdge
from archcheck.domain.model.static_call_graph import StaticCallGraph
from archcheck.domain.model.symbol_table import SymbolTable
from archcheck.domain.model.task_edge import TaskEdge
from archcheck.domain.model.task_node import TaskNode
from archcheck.domain.model.violation import Violation

__all__ = [
    # Enums
    "Visibility",
    "Severity",
    "RuleCategory",
    "CalleeKind",
    "HiddenDepType",
    "CallType",
    "EdgeNature",
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
    # Graphs (existing)
    "DiGraph",
    "ImportGraph",
    "InheritanceGraph",
    "CallGraph",
    "SymbolTable",
    # Graph algorithms
    "detect_cycles",
    "topological_order",
    # Rules
    "Rule",
    "RuleResult",
    "Violation",
    # Architecture
    "Layer",
    "Component",
    "ArchitectureDefinition",
    "ArchitectureDefinitionBuilder",
    # NEW: Runtime types (Python 3.14)
    "CallSite",
    "LibCallSite",
    "CalleeInfo",
    "RuntimeCallGraph",
    "FrozenRuntimeCallGraph",
    "TaskNode",
    "TaskEdge",
    "AsyncCallGraph",
    "CombinedCallGraph",
    # NEW: Edge types (Edge Architecture)
    "CallInstance",
    "FunctionEdge",
    "LibEdge",
    # NEW: Merged types
    "HiddenDep",
    "EntryPointCategories",
    "MergedCallGraph",
    # NEW: Validation types
    "LayerViolation",
    "FunctionInfo",
    "CoverageReport",
    "CheckStats",
    "CheckResult",
    # NEW: Configuration
    "ArchitectureConfig",
    # NEW: Static analysis types
    "StaticCallEdge",
    "StaticCallGraph",
    "InterfaceInfo",
    "ImplementationInfo",
]
