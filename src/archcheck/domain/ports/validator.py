"""Validator protocol for architecture validators.

Users extend archcheck by implementing this Protocol.
Validators check call graphs and configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, Self

if TYPE_CHECKING:
    from archcheck.domain.model.configuration import ArchitectureConfig
    from archcheck.domain.model.enums import RuleCategory
    from archcheck.domain.model.merged_call_graph import MergedCallGraph
    from archcheck.domain.model.violation import Violation


class ValidatorProtocol(Protocol):
    """Contract for validators.

    Users implement this Protocol to add custom validation logic.
    Validators are stateless and check MergedCallGraph against config.

    Key pattern: from_config() returns None if validator should be disabled.

    Example:
        class MyValidator:
            category = RuleCategory.CUSTOM

            def __init__(self, threshold: int) -> None:
                self._threshold = threshold

            def validate(
                self,
                graph: MergedCallGraph,
                config: ArchitectureConfig,
            ) -> tuple[Violation, ...]:
                violations: list[Violation] = []
                # ... validation logic ...
                return tuple(violations)

            @classmethod
            def from_config(
                cls,
                config: ArchitectureConfig,
                registry: object | None = None,
            ) -> Self | None:
                # Check if feature is enabled in config
                threshold = config.extras.get("my_threshold")
                if threshold is None:
                    return None  # Disabled
                return cls(threshold)
    """

    category: RuleCategory
    """Rule category for grouping violations."""

    def validate(
        self,
        graph: MergedCallGraph,
        config: ArchitectureConfig,
    ) -> tuple[Violation, ...]:
        """Validate architecture and return violations.

        Args:
            graph: Merged call graph (AST + Runtime)
            config: User configuration

        Returns:
            Tuple of violations found (empty if valid)
        """
        ...

    @classmethod
    def from_config(
        cls,
        config: ArchitectureConfig,
        registry: object | None = None,
    ) -> Self | None:
        """Create validator from config.

        Factory method that returns None if validator should be disabled
        based on config. This is the activation pattern.

        Args:
            config: User configuration
            registry: Optional StaticAnalysisRegistry for DI-aware validators

        Returns:
            Validator instance if enabled, None if disabled
        """
        ...
