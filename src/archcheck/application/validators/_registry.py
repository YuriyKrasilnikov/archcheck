"""Validator registry for architecture validators.

Central registry of all validators with factory functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from archcheck.application.validators._base import BaseValidator
from archcheck.application.validators.boundary_validator import BoundaryValidator
from archcheck.application.validators.cycle_validator import CycleValidator
from archcheck.application.validators.di_aware_validator import DIAwareValidator
from archcheck.domain.ports.validator import ValidatorProtocol

if TYPE_CHECKING:
    from archcheck.domain.model.configuration import ArchitectureConfig


# Registry - tuple for immutability
# Order matters: validators are run in this order
_ALL_VALIDATORS: tuple[type[BaseValidator], ...] = (
    CycleValidator,  # Always enabled
    BoundaryValidator,  # If config.allowed_imports (simple)
    DIAwareValidator,  # If config.allowed_imports + registry (DI-aware)
)


def default_validators() -> tuple[ValidatorProtocol, ...]:
    """Instantiate validators that don't require config.

    Returns:
        Tuple of always-enabled validators
    """
    return (CycleValidator(),)


def validators_from_config(
    config: ArchitectureConfig,
    registry: object | None = None,
) -> tuple[ValidatorProtocol, ...]:
    """Instantiate validators based on config.

    Validators are created using their from_config() factory method.
    If from_config() returns None, the validator is disabled.

    Args:
        config: User configuration
        registry: Optional StaticAnalysisRegistry for DI-aware validators

    Returns:
        Tuple of enabled validators
    """
    validators: list[ValidatorProtocol] = []

    for validator_cls in _ALL_VALIDATORS:
        validator = validator_cls.from_config(config, registry)
        if validator is not None:
            validators.append(validator)

    return tuple(validators)
