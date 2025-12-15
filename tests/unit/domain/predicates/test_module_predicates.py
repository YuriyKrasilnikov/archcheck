"""Tests for domain/predicates/module_predicates.py."""

from pathlib import Path

import pytest

from archcheck.domain.model.import_ import Import
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module
from archcheck.domain.predicates.module_predicates import (
    has_import,
    has_name_matching,
    is_in_package,
)


def make_location() -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=1, column=0)


def make_import(module: str) -> Import:
    """Create a valid Import."""
    return Import(module=module, name=None, alias=None, location=make_location())


def make_module(
    name: str = "myapp.services.user",
    imports: tuple[Import, ...] = (),
) -> Module:
    """Create a valid Module."""
    return Module(
        name=name,
        path=Path(f"src/{name.replace('.', '/')}.py"),
        imports=imports,
        classes=(),
        functions=(),
        constants=(),
    )


class TestIsInPackage:
    """Tests for is_in_package predicate."""

    def test_exact_match(self) -> None:
        pred = is_in_package("myapp.services.user")
        mod = make_module(name="myapp.services.user")
        assert pred(mod) is True

    def test_wildcard_match(self) -> None:
        pred = is_in_package("myapp.services.*")
        mod = make_module(name="myapp.services.user")
        assert pred(mod) is True

    def test_package_match(self) -> None:
        pred = is_in_package("myapp.services")
        mod = make_module(name="myapp.services.user")
        assert pred(mod) is True  # matches package

    def test_no_match(self) -> None:
        pred = is_in_package("myapp.domain.*")
        mod = make_module(name="myapp.services.user")
        assert pred(mod) is False

    def test_double_wildcard(self) -> None:
        pred = is_in_package("myapp.*")
        mod = make_module(name="myapp.services.deep.module")
        assert pred(mod) is True

    def test_question_mark_wildcard(self) -> None:
        pred = is_in_package("myapp.service?")
        mod = make_module(name="myapp.services")
        assert pred(mod) is True


class TestHasNameMatching:
    """Tests for has_name_matching predicate."""

    def test_simple_regex(self) -> None:
        pred = has_name_matching(r"test_.*")
        mod = make_module(name="test_module")
        assert pred(mod) is True

    def test_no_match(self) -> None:
        pred = has_name_matching(r"test_.*")
        mod = make_module(name="main")
        assert pred(mod) is False

    def test_partial_match(self) -> None:
        pred = has_name_matching(r"service")
        mod = make_module(name="myapp.services.user")
        assert pred(mod) is True

    def test_anchored_regex(self) -> None:
        pred = has_name_matching(r"^myapp\.domain")
        mod = make_module(name="myapp.domain.user")
        assert pred(mod) is True

    def test_end_anchored_regex(self) -> None:
        pred = has_name_matching(r"_test$")
        mod = make_module(name="myapp.services.user_test")
        assert pred(mod) is True

    def test_invalid_regex_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid regex"):
            has_name_matching(r"[invalid")


class TestHasImport:
    """Tests for has_import predicate."""

    def test_exact_match(self) -> None:
        pred = has_import("os")
        imports = (make_import("os"),)
        mod = make_module(imports=imports)
        assert pred(mod) is True

    def test_no_match(self) -> None:
        pred = has_import("sys")
        imports = (make_import("os"),)
        mod = make_module(imports=imports)
        assert pred(mod) is False

    def test_wildcard_match(self) -> None:
        pred = has_import("django.*")
        imports = (make_import("django.db"),)
        mod = make_module(imports=imports)
        assert pred(mod) is True

    def test_multiple_imports(self) -> None:
        pred = has_import("requests")
        imports = (make_import("os"), make_import("requests"), make_import("json"))
        mod = make_module(imports=imports)
        assert pred(mod) is True

    def test_no_imports(self) -> None:
        pred = has_import("os")
        mod = make_module(imports=())
        assert pred(mod) is False
