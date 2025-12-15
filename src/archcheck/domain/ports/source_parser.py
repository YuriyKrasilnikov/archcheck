"""Source parser port (interface)."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archcheck.domain.model.codebase import Codebase
    from archcheck.domain.model.module import Module


class SourceParserPort(ABC):
    """Port for parsing source code.

    Infrastructure layer must provide implementation.
    """

    @abstractmethod
    def parse_file(self, path: Path) -> Module:
        """Parse single Python file.

        Args:
            path: Path to .py file

        Returns:
            Parsed Module

        Raises:
            ParsingError: If file cannot be parsed
        """
        ...

    @abstractmethod
    def parse_directory(self, path: Path, package_name: str) -> Codebase:
        """Parse directory recursively.

        Args:
            path: Root directory path
            package_name: Root package name

        Returns:
            Codebase with all parsed modules

        Raises:
            ParsingError: If any file cannot be parsed
        """
        ...
