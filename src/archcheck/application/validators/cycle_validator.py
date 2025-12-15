"""Cycle detection validator.

Detects circular dependencies in the call graph using graphlib.TopologicalSorter.
Always enabled (no config required).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Self

from archcheck.application.validators._base import BaseValidator
from archcheck.domain.model.enums import RuleCategory, Severity
from archcheck.domain.model.graph import DiGraph, detect_cycles
from archcheck.domain.model.location import Location
from archcheck.domain.model.violation import Violation

if TYPE_CHECKING:
    from archcheck.domain.model.configuration import ArchitectureConfig
    from archcheck.domain.model.merged_call_graph import MergedCallGraph


class CycleValidator(BaseValidator):
    """Cycle detection validator using graphlib.TopologicalSorter.

    Detects circular dependencies in the internal call graph.
    Always enabled (no configuration required).

    Violation severity: ERROR (cycles must be fixed).
    """

    category = RuleCategory.COUPLING

    def validate(
        self,
        graph: MergedCallGraph,
        config: ArchitectureConfig,
    ) -> tuple[Violation, ...]:
        """Detect cycles in call graph.

        Args:
            graph: Merged call graph to check
            config: User configuration (unused)

        Returns:
            Tuple of violations for each detected cycle
        """
        # Build DiGraph from edge_pairs (O(1) access, no conversion)
        di_graph = DiGraph.from_edges(
            graph.edge_pairs,
            extra_nodes=graph.nodes,
        )

        # Detect cycles using graphlib
        cycles = detect_cycles(di_graph)

        if not cycles:
            return ()

        # Create violation for each cycle
        violations: list[Violation] = []
        for cycle_nodes in cycles:
            # Format cycle for message
            cycle_list = sorted(cycle_nodes)
            cycle_str = " → ".join(cycle_list[:5])
            if len(cycle_list) > 5:
                cycle_str += f" → ... ({len(cycle_list)} nodes)"

            violations.append(
                Violation(
                    rule_name="no_cycles",
                    message=f"Circular dependency detected: {cycle_str}",
                    location=Location(file=Path("."), line=1, column=0),
                    severity=Severity.ERROR,
                    category=RuleCategory.COUPLING,
                    subject=cycle_str,
                    expected="No circular dependencies",
                    actual=f"Cycle with {len(cycle_nodes)} nodes",
                    suggestion="Break the cycle by introducing an interface or restructuring",
                )
            )

        return tuple(violations)

    @classmethod
    def from_config(
        cls,
        config: ArchitectureConfig,
        registry: object | None = None,
    ) -> Self:
        """Always enabled - no config check needed."""
        return cls()
