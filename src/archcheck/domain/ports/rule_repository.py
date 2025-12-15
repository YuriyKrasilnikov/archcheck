"""Rule repository port (interface)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.enums import RuleCategory
    from archcheck.domain.model.rule import Rule


class RuleRepositoryPort(ABC):
    """Port for rule storage and retrieval.

    Infrastructure layer must provide implementation.
    """

    @abstractmethod
    def get_all_rules(self) -> Sequence[Rule]:
        """Get all registered rules.

        Returns:
            All rules
        """
        ...

    @abstractmethod
    def get_rules_by_category(self, category: RuleCategory) -> Sequence[Rule]:
        """Get rules by category.

        Args:
            category: Rule category to filter by

        Returns:
            Rules matching category
        """
        ...
