"""Parsing exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from archcheck.domain.exceptions.base import ArchCheckError

if TYPE_CHECKING:
    from pathlib import Path

    from archcheck.domain.model.location import Location


class ParsingError(ArchCheckError):
    """Error during source code parsing.

    Attributes:
        path: File that failed to parse
        reason: Why parsing failed
    """

    def __init__(self, path: Path, reason: str) -> None:
        # FAIL-FIRST: validate required parameters
        if path is None:
            raise TypeError("path must not be None")
        if not reason:
            raise ValueError("reason must be non-empty string")

        self.path = path
        self.reason = reason
        super().__init__(f"Failed to parse {path}: {reason}")


class ASTError(ParsingError):
    """Error in AST structure.

    Attributes:
        path: File with invalid AST
        location: Location of error
        reason: Why AST is invalid
    """

    def __init__(
        self,
        path: Path,
        location: Location,
        reason: str,
    ) -> None:
        # FAIL-FIRST: validate required parameters
        if location is None:
            raise TypeError("location must not be None")

        self.location = location
        super().__init__(path, f"{reason} at {location}")
