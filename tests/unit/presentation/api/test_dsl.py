"""Tests for presentation/api/dsl.py."""

from pathlib import Path

import pytest

from archcheck.domain.exceptions.base import ArchCheckError
from archcheck.domain.exceptions.violation import ArchitectureViolationError
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.import_ import Import
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module
from archcheck.presentation.api.dsl import ArchCheck, ModuleAssertion, ModuleQuery


def make_location(line: int = 1) -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=line, column=0)


def make_import(module: str, line: int = 1) -> Import:
    """Create a valid Import for tests."""
    return Import(module=module, name=None, alias=None, location=make_location(line))


def make_module(
    name: str,
    imports: tuple[Import, ...] = (),
) -> Module:
    """Create a valid Module for tests."""
    return Module(
        name=name,
        path=Path(f"{name.replace('.', '/')}.py"),
        imports=imports,
        classes=(),
        functions=(),
        constants=(),
    )


def make_codebase(*modules: Module, root_package: str = "myapp") -> Codebase:
    """Create a Codebase with given modules."""
    codebase = Codebase(root_path=Path("/test"), root_package=root_package)
    for module in modules:
        codebase.add_module(module)
    return codebase


class TestArchCheckInit:
    """Tests for ArchCheck initialization."""

    def test_none_codebase_raises(self) -> None:
        """None codebase raises TypeError."""
        with pytest.raises(TypeError, match="codebase must not be None"):
            ArchCheck(None)  # type: ignore[arg-type]

    def test_valid_codebase(self) -> None:
        """Valid codebase creates ArchCheck instance."""
        codebase = make_codebase()
        arch = ArchCheck(codebase)
        assert arch.codebase is codebase

    def test_graph_is_optional(self) -> None:
        """Graph is optional on creation."""
        codebase = make_codebase()
        arch = ArchCheck(codebase)
        with pytest.raises(ArchCheckError, match="MergedCallGraph not available"):
            _ = arch.graph


class TestArchCheckModules:
    """Tests for ArchCheck.modules()."""

    def test_modules_returns_query(self) -> None:
        """modules() returns ModuleQuery."""
        codebase = make_codebase()
        arch = ArchCheck(codebase)
        result = arch.modules()
        assert isinstance(result, ModuleQuery)

    def test_modules_query_can_execute(self) -> None:
        """modules() query can execute and return modules."""
        m1 = make_module("myapp.domain.user")
        m2 = make_module("myapp.infra.db")
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        modules = arch.modules().execute()

        assert len(modules) == 2
        assert m1 in modules
        assert m2 in modules


class TestModuleQueryFilters:
    """Tests for ModuleQuery filter methods."""

    def test_in_layer_filters(self) -> None:
        """in_layer() filters by layer name."""
        m_domain = make_module("myapp.domain.user")
        m_infra = make_module("myapp.infrastructure.db")
        codebase = make_codebase(m_domain, m_infra)
        arch = ArchCheck(codebase)

        result = arch.modules().in_layer("domain").execute()

        assert len(result) == 1
        assert result[0] is m_domain

    def test_in_package_filters_exact(self) -> None:
        """in_package() matches exact package."""
        m1 = make_module("myapp.domain")
        m2 = make_module("myapp.domain.user")
        m3 = make_module("myapp.domainx")
        codebase = make_codebase(m1, m2, m3)
        arch = ArchCheck(codebase)

        result = arch.modules().in_package("myapp.domain").execute()

        assert len(result) == 2
        assert m1 in result
        assert m2 in result
        assert m3 not in result

    def test_matching_filters_by_pattern(self) -> None:
        """matching() filters by glob pattern."""
        m1 = make_module("myapp.domain.user")
        m2 = make_module("myapp.domain.order")
        m3 = make_module("myapp.infra.db")
        codebase = make_codebase(m1, m2, m3)
        arch = ArchCheck(codebase)

        result = arch.modules().matching("myapp.domain.*").execute()

        assert len(result) == 2
        assert m1 in result
        assert m2 in result

    def test_that_filters_by_predicate(self) -> None:
        """that() filters by custom predicate."""
        m1 = make_module("myapp.domain.user")
        m2 = make_module("myapp.domain.order")
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        result = arch.modules().that(lambda m: "user" in m.name).execute()

        assert len(result) == 1
        assert result[0] is m1

    def test_chained_filters(self) -> None:
        """Multiple filters can be chained."""
        m1 = make_module("myapp.domain.user")
        m2 = make_module("myapp.domain.order")
        m3 = make_module("myapp.infra.user")
        codebase = make_codebase(m1, m2, m3)
        arch = ArchCheck(codebase)

        result = (
            arch.modules()
            .in_layer("domain")
            .that(lambda m: "user" in m.name)
            .execute()
        )

        assert len(result) == 1
        assert result[0] is m1


class TestModuleQueryShould:
    """Tests for ModuleQuery.should() transition."""

    def test_should_returns_assertion(self) -> None:
        """should() returns ModuleAssertion."""
        codebase = make_codebase(make_module("myapp.domain.user"))
        arch = ArchCheck(codebase)

        result = arch.modules().should()

        assert isinstance(result, ModuleAssertion)

    def test_should_passes_filtered_modules(self) -> None:
        """should() passes filtered modules to assertion."""
        m1 = make_module("myapp.domain.user")
        m2 = make_module("myapp.infra.db")
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        assertion = arch.modules().in_layer("domain").should()

        assert assertion.module_count == 1


class TestModuleAssertionNotImport:
    """Tests for ModuleAssertion.not_import()."""

    def test_no_patterns_raises(self) -> None:
        """not_import() with no patterns raises ValueError."""
        assertion = ModuleAssertion(_modules=())
        with pytest.raises(ValueError, match="at least one pattern required"):
            assertion.not_import()

    def test_no_violation_when_no_imports(self) -> None:
        """No violation when module has no forbidden imports."""
        m = make_module("myapp.domain.user", imports=())
        assertion = ModuleAssertion(_modules=(m,))

        violations = assertion.not_import("myapp.infra.**").collect()

        assert len(violations) == 0

    def test_violation_when_forbidden_import(self) -> None:
        """Violation when module imports forbidden pattern."""
        m = make_module(
            "myapp.domain.user",
            imports=(make_import("myapp.infrastructure.db"),),
        )
        assertion = ModuleAssertion(_modules=(m,))

        violations = assertion.not_import("myapp.infrastructure.**").collect()

        assert len(violations) == 1
        assert "no_import" in violations[0].rule_name

    def test_multiple_patterns(self) -> None:
        """Multiple patterns all checked."""
        m = make_module(
            "myapp.domain.user",
            imports=(make_import("myapp.external.api"),),
        )
        assertion = ModuleAssertion(_modules=(m,))

        violations = assertion.not_import("myapp.infra.**", "myapp.external.**").collect()

        assert len(violations) == 1


class TestModuleAssertionOnlyImport:
    """Tests for ModuleAssertion.only_import()."""

    def test_no_patterns_raises(self) -> None:
        """only_import() with no patterns raises ValueError."""
        assertion = ModuleAssertion(_modules=())
        with pytest.raises(ValueError, match="at least one pattern required"):
            assertion.only_import()

    def test_no_violation_when_allowed_imports(self) -> None:
        """No violation when all imports are allowed."""
        m = make_module(
            "myapp.domain.user",
            imports=(make_import("myapp.domain.order"),),
        )
        assertion = ModuleAssertion(_modules=(m,))

        violations = assertion.only_import("myapp.domain.**").collect()

        assert len(violations) == 0

    def test_violation_when_non_allowed_import(self) -> None:
        """Violation when module imports non-allowed."""
        m = make_module(
            "myapp.domain.user",
            imports=(make_import("myapp.infrastructure.db"),),
        )
        assertion = ModuleAssertion(_modules=(m,))

        violations = assertion.only_import("myapp.domain.**").collect()

        assert len(violations) == 1
        assert "only_import" in violations[0].rule_name


class TestModuleAssertionBeInLayer:
    """Tests for ModuleAssertion.be_in_layer()."""

    def test_no_violation_when_in_layer(self) -> None:
        """No violation when module is in expected layer."""
        m = make_module("myapp.domain.user")
        assertion = ModuleAssertion(_modules=(m,))

        violations = assertion.be_in_layer("domain").collect()

        assert len(violations) == 0

    def test_violation_when_not_in_layer(self) -> None:
        """Violation when module is not in expected layer."""
        m = make_module("myapp.infrastructure.db")
        assertion = ModuleAssertion(_modules=(m,))

        violations = assertion.be_in_layer("domain").collect()

        assert len(violations) == 1
        assert "be_in_layer" in violations[0].rule_name


class TestModuleAssertionExecution:
    """Tests for ModuleAssertion execution methods."""

    def test_collect_returns_all_violations(self) -> None:
        """collect() returns all violations."""
        m1 = make_module("myapp.domain.user", imports=(make_import("myapp.infra.db"),))
        m2 = make_module("myapp.domain.order", imports=(make_import("myapp.infra.api"),))
        assertion = ModuleAssertion(_modules=(m1, m2))

        violations = assertion.not_import("myapp.infra.**").collect()

        assert len(violations) == 2

    def test_assert_check_raises_on_violations(self) -> None:
        """assert_check() raises ArchitectureViolationError on violations."""
        m = make_module("myapp.domain.user", imports=(make_import("myapp.infra.db"),))
        assertion = ModuleAssertion(_modules=(m,))

        with pytest.raises(ArchitectureViolationError):
            assertion.not_import("myapp.infra.**").assert_check()

    def test_assert_check_passes_on_no_violations(self) -> None:
        """assert_check() does not raise when no violations."""
        m = make_module("myapp.domain.user", imports=())
        assertion = ModuleAssertion(_modules=(m,))

        # Should not raise
        assertion.not_import("myapp.infra.**").assert_check()

    def test_is_valid_true_on_no_violations(self) -> None:
        """is_valid() returns True when no violations."""
        m = make_module("myapp.domain.user", imports=())
        assertion = ModuleAssertion(_modules=(m,))

        assert assertion.not_import("myapp.infra.**").is_valid()

    def test_is_valid_false_on_violations(self) -> None:
        """is_valid() returns False when violations exist."""
        m = make_module("myapp.domain.user", imports=(make_import("myapp.infra.db"),))
        assertion = ModuleAssertion(_modules=(m,))

        assert not assertion.not_import("myapp.infra.**").is_valid()


class TestFluentChaining:
    """Tests for full fluent chain."""

    def test_full_chain_pass(self) -> None:
        """Full fluent chain passes with valid architecture."""
        m1 = make_module("myapp.domain.user", imports=(make_import("myapp.domain.order"),))
        m2 = make_module("myapp.domain.order", imports=())
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        # Should not raise
        (
            arch.modules()
            .in_layer("domain")
            .should()
            .not_import("myapp.infrastructure.**")
            .assert_check()
        )

    def test_full_chain_fail(self) -> None:
        """Full fluent chain fails with invalid architecture."""
        m = make_module(
            "myapp.domain.user",
            imports=(make_import("myapp.infrastructure.db"),),
        )
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        with pytest.raises(ArchitectureViolationError):
            (
                arch.modules()
                .in_layer("domain")
                .should()
                .not_import("myapp.infrastructure.**")
                .assert_check()
            )
