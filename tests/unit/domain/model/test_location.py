"""Tests for domain/model/location.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.location import Location


class TestLocationCreation:
    """Tests for valid Location creation."""

    def test_minimal_valid(self) -> None:
        loc = Location(file=Path("test.py"), line=1, column=0)
        assert loc.file == Path("test.py")
        assert loc.line == 1
        assert loc.column == 0
        assert loc.end_line is None
        assert loc.end_column is None

    def test_with_end_position(self) -> None:
        loc = Location(
            file=Path("test.py"),
            line=1,
            column=0,
            end_line=5,
            end_column=10,
        )
        assert loc.end_line == 5
        assert loc.end_column == 10

    def test_end_line_same_as_line(self) -> None:
        loc = Location(
            file=Path("test.py"),
            line=5,
            column=0,
            end_line=5,
            end_column=20,
        )
        assert loc.end_line == 5

    def test_is_frozen(self) -> None:
        loc = Location(file=Path("test.py"), line=1, column=0)
        with pytest.raises(AttributeError):
            loc.line = 2  # type: ignore[misc]


class TestLocationFailFirst:
    """Tests for FAIL-FIRST validation in Location."""

    def test_line_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="line must be > 0"):
            Location(file=Path("test.py"), line=0, column=0)

    def test_line_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="line must be > 0"):
            Location(file=Path("test.py"), line=-1, column=0)

    def test_column_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="column must be >= 0"):
            Location(file=Path("test.py"), line=1, column=-1)

    def test_end_line_before_line_raises(self) -> None:
        with pytest.raises(ValueError, match="end_line.*must be >= line"):
            Location(
                file=Path("test.py"),
                line=10,
                column=0,
                end_line=5,
            )


class TestLocationStr:
    """Tests for Location.__str__."""

    def test_str_format(self) -> None:
        loc = Location(file=Path("src/main.py"), line=42, column=10)
        result = str(loc)
        # Path separator varies by OS, check components
        assert "src" in result
        assert "main.py" in result
        assert ":42:10" in result

    def test_str_with_absolute_path(self) -> None:
        loc = Location(file=Path("/home/user/project/test.py"), line=1, column=0)
        result = str(loc)
        # Path separator varies by OS, check components
        assert "test.py" in result
        assert ":1:0" in result
