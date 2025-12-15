"""Tests for discovery/modules.py."""

from pathlib import Path

import pytest

from archcheck.application.discovery.modules import discover_modules


class TestDiscoverModules:
    """Tests for discover_modules function."""

    def test_discovers_python_files(self, tmp_path: Path) -> None:
        """Discovers .py files as modules."""
        (tmp_path / "domain").mkdir()
        (tmp_path / "domain" / "model.py").write_text("# model")
        (tmp_path / "domain" / "service.py").write_text("# service")

        result = discover_modules(tmp_path, "myapp")

        assert "myapp.domain.model" in result
        assert "myapp.domain.service" in result

    def test_handles_init_files(self, tmp_path: Path) -> None:
        """__init__.py becomes package name, not __init__."""
        (tmp_path / "domain").mkdir()
        (tmp_path / "domain" / "__init__.py").write_text("# init")

        result = discover_modules(tmp_path, "myapp")

        assert "myapp.domain" in result
        assert "myapp.domain.__init__" not in result

    def test_root_init(self, tmp_path: Path) -> None:
        """Root __init__.py becomes package_name."""
        (tmp_path / "__init__.py").write_text("# init")

        result = discover_modules(tmp_path, "myapp")

        assert "myapp" in result

    def test_nested_packages(self, tmp_path: Path) -> None:
        """Handles deeply nested packages."""
        (tmp_path / "domain" / "model" / "entities").mkdir(parents=True)
        (tmp_path / "domain" / "model" / "entities" / "user.py").write_text("# user")

        result = discover_modules(tmp_path, "myapp")

        assert "myapp.domain.model.entities.user" in result

    def test_excludes_pycache(self, tmp_path: Path) -> None:
        """Excludes __pycache__ directories."""
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "module.cpython-314.pyc").write_text("# cache")
        (tmp_path / "domain.py").write_text("# domain")

        result = discover_modules(tmp_path, "myapp")

        assert "myapp.domain" in result
        assert not any("pycache" in m for m in result)

    def test_excludes_invalid_identifiers(self, tmp_path: Path) -> None:
        """Excludes paths with invalid Python identifiers."""
        (tmp_path / "valid").mkdir()
        (tmp_path / "valid" / "module.py").write_text("# ok")
        (tmp_path / "123-invalid").mkdir()
        (tmp_path / "123-invalid" / "other.py").write_text("# bad")

        result = discover_modules(tmp_path, "myapp")

        assert "myapp.valid.module" in result
        assert not any("invalid" in m for m in result)

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns empty set."""
        result = discover_modules(tmp_path, "myapp")

        assert result == frozenset()

    def test_not_directory_raises(self, tmp_path: Path) -> None:
        """Raises ValueError if app_dir is not a directory."""
        file_path = tmp_path / "file.py"
        file_path.write_text("# module")

        with pytest.raises(ValueError, match="must be a directory"):
            discover_modules(file_path, "myapp")

    def test_empty_package_name_raises(self, tmp_path: Path) -> None:
        """Raises ValueError if package_name is empty."""
        with pytest.raises(ValueError, match="must not be empty"):
            discover_modules(tmp_path, "")
