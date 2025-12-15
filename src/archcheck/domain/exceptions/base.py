"""Base exceptions for archcheck domain."""


class ArchCheckError(Exception):
    """Root exception for all archcheck errors.

    All domain exceptions inherit from this.
    Allows catching all archcheck-specific errors.
    """
