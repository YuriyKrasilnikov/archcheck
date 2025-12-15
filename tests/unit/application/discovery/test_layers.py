"""Tests for discovery/layers.py."""

from pathlib import Path

import pytest

from archcheck.application.discovery.layers import discover_layers


class TestDiscoverLayers:
    """Tests for discover_layers function."""

    def test_discovers_directories(self, tmp_path: Path) -> None:
        """Discovers valid Python identifier directories."""
        (tmp_path / "domain").mkdir()
        (tmp_path / "application").mkdir()
        (tmp_path / "infrastructure").mkdir()

        result = discover_layers(tmp_path)

        assert result == frozenset({"domain", "application", "infrastructure"})

    def test_excludes_underscore_prefix(self, tmp_path: Path) -> None:
        """Directories starting with underscore are excluded."""
        (tmp_path / "domain").mkdir()
        (tmp_path / "_internal").mkdir()
        (tmp_path / "__pycache__").mkdir()

        result = discover_layers(tmp_path)

        assert result == frozenset({"domain"})

    def test_excludes_non_identifiers(self, tmp_path: Path) -> None:
        """Directories with invalid Python identifiers are excluded."""
        (tmp_path / "domain").mkdir()
        (tmp_path / "my-dir").mkdir()  # hyphen not allowed
        (tmp_path / "123abc").mkdir()  # starts with digit

        result = discover_layers(tmp_path)

        assert result == frozenset({"domain"})

    def test_excludes_files(self, tmp_path: Path) -> None:
        """Files are not included, only directories."""
        (tmp_path / "domain").mkdir()
        (tmp_path / "module.py").write_text("# module")

        result = discover_layers(tmp_path)

        assert result == frozenset({"domain"})

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns empty set."""
        result = discover_layers(tmp_path)

        assert result == frozenset()

    def test_not_directory_raises(self, tmp_path: Path) -> None:
        """Raises ValueError if app_dir is not a directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="must be a directory"):
            discover_layers(file_path)

    def test_nonexistent_raises(self, tmp_path: Path) -> None:
        """Raises ValueError if app_dir does not exist."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="must be a directory"):
            discover_layers(nonexistent)
