"""Tests for domain/exceptions/parsing.py."""

from pathlib import Path

import pytest

from archcheck.domain.exceptions.base import ArchCheckError
from archcheck.domain.exceptions.parsing import ASTError, ParsingError
from archcheck.domain.model.location import Location


class TestParsingError:
    """Tests for ParsingError exception."""

    def test_is_archcheck_error(self) -> None:
        assert issubclass(ParsingError, ArchCheckError)

    def test_has_path_attribute(self) -> None:
        path = Path("test.py")
        err = ParsingError(path, "syntax error")
        assert err.path == path

    def test_has_reason_attribute(self) -> None:
        err = ParsingError(Path("test.py"), "syntax error")
        assert err.reason == "syntax error"

    def test_message_format(self) -> None:
        err = ParsingError(Path("src/main.py"), "invalid syntax at line 10")
        result = str(err)
        # Path separator varies by OS
        assert "Failed to parse" in result
        assert "main.py" in result
        assert "invalid syntax at line 10" in result

    def test_can_catch_as_archcheck_error(self) -> None:
        with pytest.raises(ArchCheckError) as exc_info:
            raise ParsingError(Path("test.py"), "error")
        assert isinstance(exc_info.value, ParsingError)


class TestASTError:
    """Tests for ASTError exception."""

    def test_is_parsing_error(self) -> None:
        assert issubclass(ASTError, ParsingError)

    def test_has_location_attribute(self) -> None:
        loc = Location(file=Path("test.py"), line=10, column=5)
        err = ASTError(Path("test.py"), loc, "unexpected node")
        assert err.location == loc

    def test_inherits_path(self) -> None:
        loc = Location(file=Path("test.py"), line=10, column=5)
        err = ASTError(Path("test.py"), loc, "unexpected node")
        assert err.path == Path("test.py")

    def test_message_includes_location(self) -> None:
        loc = Location(file=Path("test.py"), line=10, column=5)
        err = ASTError(Path("src/module.py"), loc, "invalid AST structure")
        assert "test.py:10:5" in str(err)
        assert "invalid AST structure" in str(err)

    def test_can_catch_as_parsing_error(self) -> None:
        loc = Location(file=Path("test.py"), line=1, column=0)
        with pytest.raises(ParsingError) as exc_info:
            raise ASTError(Path("test.py"), loc, "error")
        assert isinstance(exc_info.value, ASTError)
