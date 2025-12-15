"""Tests for collectors/classifier.py."""

from pathlib import Path

from archcheck.application.collectors.classifier import classify_callee
from archcheck.domain.model.callee_kind import CalleeKind


class TestClassifyCallee:
    """Tests for classify_callee function."""

    def test_app_code(self, tmp_path: Path) -> None:
        """Code under base_dir (not tests) is APP."""
        base_dir = tmp_path / "myapp"
        base_dir.mkdir()
        (base_dir / "domain").mkdir(parents=True)
        app_file = base_dir / "domain" / "model.py"
        app_file.write_text("# app code")

        result = classify_callee(str(app_file), base_dir, frozenset())

        assert result.kind == CalleeKind.APP
        assert result.module == "domain.model"

    def test_test_code(self, tmp_path: Path) -> None:
        """Code under tests/ directory is TEST."""
        base_dir = tmp_path / "myapp"
        base_dir.mkdir()
        tests_dir = base_dir / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_model.py"
        test_file.write_text("# test code")

        result = classify_callee(str(test_file), base_dir, frozenset())

        assert result.kind == CalleeKind.TEST
        assert result.module == "tests.test_model"

    def test_lib_code_known(self, tmp_path: Path) -> None:
        """Known library code is LIB."""
        # Simulate a path that looks like site-packages
        # Since we can't easily mock site-packages, test the editable install path
        base_dir = tmp_path / "myapp"
        base_dir.mkdir()

        # Path contains known lib name → LIB
        lib_path = tmp_path / "other_project" / "aiohttp" / "client.py"
        lib_path.parent.mkdir(parents=True)
        lib_path.write_text("# lib code")

        result = classify_callee(str(lib_path), base_dir, frozenset({"aiohttp"}))

        assert result.kind == CalleeKind.LIB
        assert result.lib_name == "aiohttp"

    def test_lib_code_unknown(self, tmp_path: Path) -> None:
        """Unknown external code is OTHER."""
        base_dir = tmp_path / "myapp"
        base_dir.mkdir()

        # Path contains unknown lib name → OTHER
        lib_path = tmp_path / "other_project" / "unknown" / "module.py"
        lib_path.parent.mkdir(parents=True)
        lib_path.write_text("# unknown code")

        result = classify_callee(str(lib_path), base_dir, frozenset({"aiohttp"}))

        assert result.kind == CalleeKind.OTHER

    def test_stdlib_is_other(self, tmp_path: Path) -> None:
        """stdlib code is OTHER."""
        base_dir = tmp_path / "myapp"
        base_dir.mkdir()

        # Use a path that looks like stdlib (outside project and site-packages)
        stdlib_path = "/usr/lib/python3.14/json/__init__.py"

        result = classify_callee(stdlib_path, base_dir, frozenset({"aiohttp"}))

        assert result.kind == CalleeKind.OTHER

    def test_nested_app_code(self, tmp_path: Path) -> None:
        """Deeply nested app code is classified correctly."""
        base_dir = tmp_path / "myapp"
        (base_dir / "domain" / "model" / "entities").mkdir(parents=True)
        app_file = base_dir / "domain" / "model" / "entities" / "user.py"
        app_file.write_text("# user entity")

        result = classify_callee(str(app_file), base_dir, frozenset())

        assert result.kind == CalleeKind.APP
        assert result.module == "domain.model.entities.user"

    def test_init_file(self, tmp_path: Path) -> None:
        """__init__.py becomes package name."""
        base_dir = tmp_path / "myapp"
        (base_dir / "domain").mkdir(parents=True)
        init_file = base_dir / "domain" / "__init__.py"
        init_file.write_text("# init")

        result = classify_callee(str(init_file), base_dir, frozenset())

        assert result.kind == CalleeKind.APP
        assert result.module == "domain"
