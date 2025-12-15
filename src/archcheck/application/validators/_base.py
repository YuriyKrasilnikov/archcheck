"""Base validator class for architecture validators.

Provides default implementation of ValidatorProtocol.
Concrete validators inherit from this.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from archcheck.domain.model.configuration import ArchitectureConfig
    from archcheck.domain.model.enums import RuleCategory
    from archcheck.domain.model.merged_call_graph import MergedCallGraph
    from archcheck.domain.model.violation import Violation


class BaseValidator(ABC):
    """Base class for validators implementing ValidatorProtocol.

    Concrete validators must:
    1. Set `category` class attribute
    2. Implement `validate()` method
    3. Optionally override `from_config()` for conditional activation

    Example:
        class MyValidator(BaseValidator):
            category = RuleCategory.CUSTOM

            def __init__(self, threshold: int) -> None:
                self._threshold = threshold

            def validate(
                self,
                graph: MergedCallGraph,
                config: ArchitectureConfig,
            ) -> tuple[Violation, ...]:
                # ... validation logic ...
                return tuple(violations)

            @classmethod
            def from_config(
                cls,
                config: ArchitectureConfig,
                registry: object | None = None,
            ) -> Self | None:
                threshold = config.extras.get("my_threshold")
                if threshold is None:
                    return None  # Disabled
                return cls(threshold)
    """

    category: RuleCategory
    """Rule category for grouping violations."""

    @abstractmethod
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

    @classmethod
    def from_config(
        cls,
        config: ArchitectureConfig,
        registry: object | None = None,
    ) -> Self | None:
        """Create validator from config.

        Default: always enabled (returns new instance).
        Override in subclass for conditional activation.

        Args:
            config: User configuration
            registry: Optional StaticAnalysisRegistry

        Returns:
            Validator instance if enabled, None if disabled
        """
        return cls()
