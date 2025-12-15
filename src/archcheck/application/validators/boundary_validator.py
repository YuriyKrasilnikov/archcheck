"""Layer boundary validator.

Validates that modules only import from allowed layers.
Enabled when config.allowed_imports is set.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Self

from archcheck.application.validators._base import BaseValidator
from archcheck.domain.model.enums import RuleCategory, Severity
from archcheck.domain.model.violation import Violation

if TYPE_CHECKING:
    from archcheck.domain.model.configuration import ArchitectureConfig
    from archcheck.domain.model.merged_call_graph import MergedCallGraph


def _get_layer(fqn: str) -> str:
    """Extract layer name from fully qualified name.

    Layer is the first component of the FQN after the root package.

    Examples:
        "myapp.domain.model.user" → "domain"
        "myapp.services.auth" → "services"
        "myapp" → "myapp" (root module, no layer)

    Args:
        fqn: Fully qualified module/function name

    Returns:
        Layer name (first path component after root)
    """
    parts = fqn.split(".")
    if len(parts) < 2:
        return fqn  # No layer, just root
    return parts[1]  # Second component is the layer


class BoundaryValidator(BaseValidator):
    """Layer boundary validator.

    Validates that internal edges respect layer boundaries.
    Caller layer must be allowed to depend on callee layer.

    Enabled when config.allowed_imports is set.
    Violation severity: ERROR.
    """

    category = RuleCategory.BOUNDARIES

    def __init__(self, allowed: Mapping[str, frozenset[str]]) -> None:
        """Initialize with allowed imports mapping.

        Args:
            allowed: Layer → set of allowed layers to depend on
        """
        if not allowed:
            raise ValueError("allowed imports mapping must not be empty")
        self._allowed = allowed

    def validate(
        self,
        graph: MergedCallGraph,
        config: ArchitectureConfig,
    ) -> tuple[Violation, ...]:
        """Validate layer boundaries.

        Only checks DIRECT edges (boundary-relevant).
        PARAMETRIC, INHERITED, FRAMEWORK edges are skipped.

        Args:
            graph: Merged call graph
            config: User configuration (unused - allowed from __init__)

        Returns:
            Tuple of violations for boundary crossings
        """
        violations: list[Violation] = []

        # Only check direct_edges (boundary-relevant)
        for edge in graph.direct_edges:
            caller_layer = _get_layer(edge.caller_fqn)
            callee_layer = _get_layer(edge.callee_fqn)

            # Same layer is always allowed
            if caller_layer == callee_layer:
                continue

            # Check if caller layer is allowed to depend on callee layer
            allowed_for_caller = self._allowed.get(caller_layer, frozenset())
            if callee_layer not in allowed_for_caller:
                violations.append(
                    Violation(
                        rule_name="layer_boundary",
                        message=f"Layer '{caller_layer}' cannot depend on '{callee_layer}'",
                        location=edge.first_location,
                        severity=Severity.ERROR,
                        category=RuleCategory.BOUNDARIES,
                        subject=f"{edge.caller_fqn} → {edge.callee_fqn}",
                        expected=f"Imports from: {sorted(allowed_for_caller)}",
                        actual=f"Import from: {callee_layer}",
                        suggestion="Move code to allowed layer or update allowed_imports config",
                    )
                )

        return tuple(violations)

    @classmethod
    def from_config(
        cls,
        config: ArchitectureConfig,
        registry: object | None = None,
    ) -> Self | None:
        """Create from config if allowed_imports is set.

        Args:
            config: User configuration
            registry: Unused

        Returns:
            BoundaryValidator if allowed_imports configured, else None
        """
        if config.allowed_imports is None:
            return None  # Disabled
        return cls(config.allowed_imports)
