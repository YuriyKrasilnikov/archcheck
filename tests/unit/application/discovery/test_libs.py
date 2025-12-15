"""Tests for discovery/libs.py."""

from pathlib import Path

import pytest

from archcheck.application.discovery.libs import load_known_libs


class TestLoadKnownLibs:
    """Tests for load_known_libs function."""

    def test_parses_requirements_file(self, tmp_path: Path) -> None:
        """Parses package names from requirements.txt."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("aiohttp==3.9.0\nrequests>=2.28.0\npydantic")

        result = load_known_libs(req_file)

        assert "aiohttp" in result
        assert "requests" in result
        assert "pydantic" in result

    def test_normalizes_names(self, tmp_path: Path) -> None:
        """Normalizes package names (lowercase, - and . to _)."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("Scikit-Learn\nruamel.yaml\nFlask-RESTful")

        result = load_known_libs(req_file)

        assert "scikit_learn" in result
        assert "ruamel_yaml" in result
        assert "flask_restful" in result

    def test_skips_comments(self, tmp_path: Path) -> None:
        """Skips comment lines."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("# This is a comment\naiohttp\n# Another comment")

        result = load_known_libs(req_file)

        assert result == frozenset({"aiohttp"})

    def test_skips_options(self, tmp_path: Path) -> None:
        """Skips pip options (-r, -e, etc.)."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("-r base.txt\n-e git+https://...\naiohttp\n--index-url ...")

        result = load_known_libs(req_file)

        assert result == frozenset({"aiohttp"})

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        """Skips empty lines."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("aiohttp\n\n\nrequests")

        result = load_known_libs(req_file)

        assert result == frozenset({"aiohttp", "requests"})

    def test_handles_extras(self, tmp_path: Path) -> None:
        """Handles packages with extras [extra]."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("uvicorn[standard]\npydantic[email]")

        result = load_known_libs(req_file)

        assert "uvicorn" in result
        assert "pydantic" in result

    def test_parses_directory(self, tmp_path: Path) -> None:
        """Parses all .txt files in directory."""
        req_dir = tmp_path / "requirements"
        req_dir.mkdir()
        (req_dir / "base.txt").write_text("aiohttp\nrequests")
        (req_dir / "dev.txt").write_text("pytest\nmypy")

        result = load_known_libs(req_dir)

        assert result == frozenset({"aiohttp", "requests", "pytest", "mypy"})

    def test_directory_no_txt_raises(self, tmp_path: Path) -> None:
        """Raises ValueError if directory has no .txt files."""
        req_dir = tmp_path / "requirements"
        req_dir.mkdir()
        (req_dir / "readme.md").write_text("# readme")

        with pytest.raises(ValueError, match="no .txt files"):
            load_known_libs(req_dir)

    def test_nonexistent_raises(self, tmp_path: Path) -> None:
        """Raises FileNotFoundError for nonexistent path."""
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            load_known_libs(nonexistent)

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty file returns empty set."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("")

        result = load_known_libs(req_file)

        assert result == frozenset()
