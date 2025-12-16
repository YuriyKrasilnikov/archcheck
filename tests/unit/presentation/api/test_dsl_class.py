"""Tests for ClassQuery and ClassAssertion in presentation/api/dsl.py."""

from pathlib import Path

import pytest

from archcheck.domain.exceptions.violation import ArchitectureViolationError
from archcheck.domain.model.class_ import Class
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module
from archcheck.presentation.api.dsl import ArchCheck, ClassAssertion, ClassQuery


def make_location(line: int = 1) -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=line, column=0)


def make_method(
    name: str,
    qualified_name: str,
    visibility: Visibility = Visibility.PUBLIC,
) -> Function:
    """Create a valid method Function for tests."""
    return Function(
        name=name,
        qualified_name=qualified_name,
        parameters=(),
        return_annotation=None,
        decorators=(),
        location=make_location(),
        visibility=visibility,
        is_method=True,
    )


def make_class(
    name: str,
    qualified_name: str,
    bases: tuple[str, ...] = (),
    methods: tuple[Function, ...] = (),
) -> Class:
    """Create a valid Class for tests."""
    return Class(
        name=name,
        qualified_name=qualified_name,
        bases=bases,
        decorators=(),
        methods=methods,
        attributes=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
    )


def make_module(
    name: str,
    classes: tuple[Class, ...] = (),
) -> Module:
    """Create a valid Module for tests."""
    return Module(
        name=name,
        path=Path(f"{name.replace('.', '/')}.py"),
        imports=(),
        classes=classes,
        functions=(),
        constants=(),
    )


def make_codebase(*modules: Module, root_package: str = "myapp") -> Codebase:
    """Create a Codebase with given modules."""
    codebase = Codebase(root_path=Path("/test"), root_package=root_package)
    for module in modules:
        codebase.add_module(module)
    return codebase


class TestArchCheckClasses:
    """Tests for ArchCheck.classes()."""

    def test_classes_returns_query(self) -> None:
        """classes() returns ClassQuery."""
        codebase = make_codebase()
        arch = ArchCheck(codebase)
        result = arch.classes()
        assert isinstance(result, ClassQuery)

    def test_classes_query_can_execute(self) -> None:
        """classes() query can execute and return classes."""
        c1 = make_class("User", "myapp.domain.user.User")
        c2 = make_class("DB", "myapp.infra.db.DB")
        m1 = make_module("myapp.domain.user", classes=(c1,))
        m2 = make_module("myapp.infra.db", classes=(c2,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        classes = arch.classes().execute()

        assert len(classes) == 2


class TestClassQueryFilters:
    """Tests for ClassQuery filter methods."""

    def test_in_layer_filters(self) -> None:
        """in_layer() filters by layer name."""
        c_domain = make_class("User", "myapp.domain.user.User")
        c_infra = make_class("DB", "myapp.infrastructure.db.DB")
        m1 = make_module("myapp.domain.user", classes=(c_domain,))
        m2 = make_module("myapp.infrastructure.db", classes=(c_infra,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        result = arch.classes().in_layer("domain").execute()

        assert len(result) == 1
        assert result[0] is c_domain

    def test_in_package_filters(self) -> None:
        """in_package() filters by package prefix."""
        c1 = make_class("User", "myapp.domain.user.User")
        c2 = make_class("Order", "myapp.domain.order.Order")
        c3 = make_class("DB", "myapp.infra.db.DB")
        m1 = make_module("myapp.domain.user", classes=(c1,))
        m2 = make_module("myapp.domain.order", classes=(c2,))
        m3 = make_module("myapp.infra.db", classes=(c3,))
        codebase = make_codebase(m1, m2, m3)
        arch = ArchCheck(codebase)

        result = arch.classes().in_package("myapp.domain").execute()

        assert len(result) == 2
        assert c1 in result
        assert c2 in result

    def test_matching_filters_by_qualified_name(self) -> None:
        """matching() filters by qualified name pattern."""
        c1 = make_class("User", "myapp.domain.user.User")
        c2 = make_class("UserService", "myapp.domain.user.UserService")
        c3 = make_class("DB", "myapp.infra.db.DB")
        m1 = make_module("myapp.domain.user", classes=(c1, c2))
        m2 = make_module("myapp.infra.db", classes=(c3,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        result = arch.classes().matching("myapp.domain.**").execute()

        assert len(result) == 2
        assert c1 in result
        assert c2 in result

    def test_named_filters_by_class_name(self) -> None:
        """named() filters by class name pattern."""
        c1 = make_class("UserRepository", "myapp.domain.user.UserRepository")
        c2 = make_class("OrderRepository", "myapp.domain.order.OrderRepository")
        c3 = make_class("UserService", "myapp.domain.user.UserService")
        m1 = make_module("myapp.domain.user", classes=(c1, c3))
        m2 = make_module("myapp.domain.order", classes=(c2,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        result = arch.classes().named("*Repository").execute()

        assert len(result) == 2
        assert c1 in result
        assert c2 in result

    def test_extending_filters_by_base(self) -> None:
        """extending() filters by base class."""
        c1 = make_class("UserRepo", "myapp.repo.UserRepo", bases=("BaseRepository",))
        c2 = make_class("UserService", "myapp.svc.UserService", bases=("BaseService",))
        m1 = make_module("myapp.repo", classes=(c1,))
        m2 = make_module("myapp.svc", classes=(c2,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        result = arch.classes().extending("Base*").execute()

        assert len(result) == 2

    def test_that_filters_by_predicate(self) -> None:
        """that() filters by custom predicate."""
        c1 = make_class("User", "myapp.domain.User", bases=("Protocol",))
        c2 = make_class("Order", "myapp.domain.Order", bases=())
        m = make_module("myapp.domain", classes=(c1, c2))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        result = arch.classes().that(lambda c: "Protocol" in c.bases).execute()

        assert len(result) == 1
        assert result[0] is c1

    def test_chained_filters(self) -> None:
        """Multiple filters can be chained."""
        c1 = make_class("UserRepository", "myapp.domain.UserRepository")
        c2 = make_class("OrderRepository", "myapp.infra.OrderRepository")
        c3 = make_class("UserService", "myapp.domain.UserService")
        m1 = make_module("myapp.domain", classes=(c1, c3))
        m2 = make_module("myapp.infra", classes=(c2,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        result = arch.classes().in_layer("domain").named("*Repository").execute()

        assert len(result) == 1
        assert result[0] is c1


class TestClassQueryShould:
    """Tests for ClassQuery.should() transition."""

    def test_should_returns_assertion(self) -> None:
        """should() returns ClassAssertion."""
        c = make_class("User", "myapp.domain.User")
        m = make_module("myapp.domain", classes=(c,))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        result = arch.classes().should()

        assert isinstance(result, ClassAssertion)

    def test_should_passes_filtered_classes(self) -> None:
        """should() passes filtered classes to assertion."""
        c1 = make_class("User", "myapp.domain.User")
        c2 = make_class("DB", "myapp.infra.DB")
        m1 = make_module("myapp.domain", classes=(c1,))
        m2 = make_module("myapp.infra", classes=(c2,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        assertion = arch.classes().in_layer("domain").should()

        assert assertion.class_count == 1


class TestClassAssertionExtend:
    """Tests for ClassAssertion.extend()."""

    def test_no_violation_when_extends(self) -> None:
        """No violation when class extends base."""
        c = make_class("UserRepo", "myapp.UserRepo", bases=("BaseRepository",))
        assertion = ClassAssertion(_classes=(c,))

        violations = assertion.extend("BaseRepository").collect()

        assert len(violations) == 0

    def test_violation_when_not_extends(self) -> None:
        """Violation when class doesn't extend base."""
        c = make_class("UserRepo", "myapp.UserRepo", bases=())
        assertion = ClassAssertion(_classes=(c,))

        violations = assertion.extend("BaseRepository").collect()

        assert len(violations) == 1
        assert "extend" in violations[0].rule_name


class TestClassAssertionImplement:
    """Tests for ClassAssertion.implement()."""

    def test_no_violation_when_implements(self) -> None:
        """No violation when class implements protocol."""
        c = make_class("UserRepo", "myapp.UserRepo", bases=("RepositoryProtocol",))
        assertion = ClassAssertion(_classes=(c,))

        violations = assertion.implement("*Protocol").collect()

        assert len(violations) == 0

    def test_violation_when_not_implements(self) -> None:
        """Violation when class doesn't implement protocol."""
        c = make_class("UserRepo", "myapp.UserRepo", bases=())
        assertion = ClassAssertion(_classes=(c,))

        violations = assertion.implement("*Protocol").collect()

        assert len(violations) == 1
        assert "implement" in violations[0].rule_name


class TestClassAssertionBeInLayer:
    """Tests for ClassAssertion.be_in_layer()."""

    def test_no_violation_when_in_layer(self) -> None:
        """No violation when class is in expected layer."""
        c = make_class("User", "myapp.domain.User")
        assertion = ClassAssertion(_classes=(c,))

        violations = assertion.be_in_layer("domain").collect()

        assert len(violations) == 0

    def test_violation_when_not_in_layer(self) -> None:
        """Violation when class is not in expected layer."""
        c = make_class("User", "myapp.infrastructure.User")
        assertion = ClassAssertion(_classes=(c,))

        violations = assertion.be_in_layer("domain").collect()

        assert len(violations) == 1
        assert "be_in_layer" in violations[0].rule_name


class TestClassAssertionHaveMaxMethods:
    """Tests for ClassAssertion.have_max_methods()."""

    def test_invalid_max_raises(self) -> None:
        """max_methods < 1 raises ValueError."""
        assertion = ClassAssertion(_classes=())
        with pytest.raises(ValueError, match="max methods must be >= 1"):
            assertion.have_max_methods(0)

    def test_no_violation_when_under_limit(self) -> None:
        """No violation when public methods <= limit."""
        methods = (
            make_method("foo", "myapp.User.foo"),
            make_method("bar", "myapp.User.bar"),
        )
        c = make_class("User", "myapp.User", methods=methods)
        assertion = ClassAssertion(_classes=(c,))

        violations = assertion.have_max_methods(5).collect()

        assert len(violations) == 0

    def test_violation_when_over_limit(self) -> None:
        """Violation when public methods > limit."""
        methods = tuple(make_method(f"m{i}", f"myapp.User.m{i}") for i in range(10))
        c = make_class("User", "myapp.User", methods=methods)
        assertion = ClassAssertion(_classes=(c,))

        violations = assertion.have_max_methods(5).collect()

        assert len(violations) == 1
        assert "max_methods" in violations[0].rule_name

    def test_only_counts_public_methods(self) -> None:
        """Only public methods are counted."""
        methods = (
            make_method("public1", "myapp.User.public1", Visibility.PUBLIC),
            make_method("public2", "myapp.User.public2", Visibility.PUBLIC),
            make_method("_protected", "myapp.User._protected", Visibility.PROTECTED),
            make_method("__private", "myapp.User.__private", Visibility.PRIVATE),
        )
        c = make_class("User", "myapp.User", methods=methods)
        assertion = ClassAssertion(_classes=(c,))

        violations = assertion.have_max_methods(2).collect()

        assert len(violations) == 0


class TestClassAssertionExecution:
    """Tests for ClassAssertion execution methods."""

    def test_assert_check_raises_on_violations(self) -> None:
        """assert_check() raises ArchitectureViolationError on violations."""
        c = make_class("User", "myapp.infra.User")
        assertion = ClassAssertion(_classes=(c,))

        with pytest.raises(ArchitectureViolationError):
            assertion.be_in_layer("domain").assert_check()

    def test_assert_check_passes_on_no_violations(self) -> None:
        """assert_check() does not raise when no violations."""
        c = make_class("User", "myapp.domain.User")
        assertion = ClassAssertion(_classes=(c,))

        # Should not raise
        assertion.be_in_layer("domain").assert_check()

    def test_is_valid_true_on_no_violations(self) -> None:
        """is_valid() returns True when no violations."""
        c = make_class("User", "myapp.domain.User")
        assertion = ClassAssertion(_classes=(c,))

        assert assertion.be_in_layer("domain").is_valid()

    def test_is_valid_false_on_violations(self) -> None:
        """is_valid() returns False when violations exist."""
        c = make_class("User", "myapp.infra.User")
        assertion = ClassAssertion(_classes=(c,))

        assert not assertion.be_in_layer("domain").is_valid()


class TestClassFluentChaining:
    """Tests for full fluent chain with classes."""

    def test_full_chain_pass(self) -> None:
        """Full fluent chain passes with valid architecture."""
        c = make_class(
            "UserRepository",
            "myapp.infrastructure.UserRepository",
            bases=("RepositoryProtocol",),
        )
        m = make_module("myapp.infrastructure", classes=(c,))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        # Should not raise
        (
            arch.classes()
            .named("*Repository")
            .should()
            .be_in_layer("infrastructure")
            .implement("*Protocol")
            .assert_check()
        )

    def test_full_chain_fail(self) -> None:
        """Full fluent chain fails with invalid architecture."""
        c = make_class("UserRepository", "myapp.domain.UserRepository", bases=())
        m = make_module("myapp.domain", classes=(c,))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        with pytest.raises(ArchitectureViolationError):
            (
                arch.classes()
                .named("*Repository")
                .should()
                .be_in_layer("infrastructure")
                .assert_check()
            )
