"""Tests for path filters.

Tests:
- include_paths: filter by file path fnmatch patterns
- exclude_paths: filter by file path fnmatch patterns

Note: fnmatch uses * to match any characters INCLUDING /.
"""

from archcheck.infrastructure.filters.path import exclude_paths, include_paths
from tests.factories import make_call_event


class TestIncludePaths:
    """Tests for include_paths filter."""

    def test_include_exact_path(self) -> None:
        """include_paths matches exact path."""
        flt = include_paths("src/main.py")

        assert flt(make_call_event(file="src/main.py")) is True
        assert flt(make_call_event(file="src/other.py")) is False

    def test_include_glob_star(self) -> None:
        """include_paths * matches any characters including /."""
        flt = include_paths("*.py")

        assert flt(make_call_event(file="main.py")) is True
        assert flt(make_call_event(file="src/main.py")) is True
        assert flt(make_call_event(file="src/sub/main.py")) is True
        assert flt(make_call_event(file="main.txt")) is False

    def test_include_multiple_patterns(self) -> None:
        """include_paths matches any of multiple patterns."""
        flt = include_paths("src/*", "lib/*")

        assert flt(make_call_event(file="src/main.py")) is True
        assert flt(make_call_event(file="lib/utils.py")) is True
        assert flt(make_call_event(file="tests/test.py")) is False

    def test_include_none_file(self) -> None:
        """include_paths returns False for events with None file."""
        flt = include_paths("src/*")

        assert flt(make_call_event(file=None)) is False


class TestExcludePaths:
    """Tests for exclude_paths filter."""

    def test_exclude_exact_path(self) -> None:
        """exclude_paths excludes exact path."""
        flt = exclude_paths("src/main.py")

        assert flt(make_call_event(file="src/main.py")) is False
        assert flt(make_call_event(file="src/other.py")) is True

    def test_exclude_glob_pattern(self) -> None:
        """exclude_paths excludes by fnmatch pattern."""
        flt = exclude_paths("*test_*")

        assert flt(make_call_event(file="tests/test_main.py")) is False
        assert flt(make_call_event(file="src/main.py")) is True

    def test_exclude_venv_pattern(self) -> None:
        """exclude_paths excludes .venv directory."""
        flt = exclude_paths("*.venv*")

        assert flt(make_call_event(file=".venv/lib/python.py")) is False
        assert flt(make_call_event(file="project/.venv/lib.py")) is False
        assert flt(make_call_event(file="src/main.py")) is True

    def test_exclude_multiple_patterns(self) -> None:
        """exclude_paths excludes any of multiple patterns."""
        flt = exclude_paths("*.venv*", "*test_*")

        assert flt(make_call_event(file=".venv/lib.py")) is False
        assert flt(make_call_event(file="tests/test_main.py")) is False
        assert flt(make_call_event(file="src/main.py")) is True

    def test_exclude_none_file(self) -> None:
        """exclude_paths returns True for events with None file."""
        flt = exclude_paths("*test_*")

        # None file doesn't match any pattern, so not excluded
        assert flt(make_call_event(file=None)) is True
