"""Tests for FunctionQuery and FunctionAssertion in presentation/api/dsl.py."""

from pathlib import Path

import pytest

from archcheck.domain.exceptions.violation import ArchitectureViolationError
from archcheck.domain.model.call_info import CallInfo
from archcheck.domain.model.call_type import CallType
from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.class_ import Class
from archcheck.domain.model.enums import Visibility
from archcheck.domain.model.function import Function
from archcheck.domain.model.location import Location
from archcheck.domain.model.module import Module
from archcheck.presentation.api.dsl import ArchCheck, FunctionAssertion, FunctionQuery


def make_location(line: int = 1) -> Location:
    """Create a valid Location for tests."""
    return Location(file=Path("test.py"), line=line, column=0)


def make_call_info(callee: str, resolved: str | None = None, line: int = 1) -> CallInfo:
    """Create a valid CallInfo for tests."""
    return CallInfo(
        callee_name=callee,
        resolved_fqn=resolved,
        line=line,
        call_type=CallType.FUNCTION,
    )


def make_function(
    name: str,
    qualified_name: str,
    is_async: bool = False,
    is_method: bool = False,
    body_calls: tuple[CallInfo, ...] = (),
) -> Function:
    """Create a valid Function for tests."""
    return Function(
        name=name,
        qualified_name=qualified_name,
        parameters=(),
        return_annotation=None,
        decorators=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
        is_async=is_async,
        is_method=is_method,
        body_calls=body_calls,
    )


def make_class(
    name: str,
    qualified_name: str,
    methods: tuple[Function, ...] = (),
) -> Class:
    """Create a valid Class for tests."""
    return Class(
        name=name,
        qualified_name=qualified_name,
        bases=(),
        decorators=(),
        methods=methods,
        attributes=(),
        location=make_location(),
        visibility=Visibility.PUBLIC,
    )


def make_module(
    name: str,
    functions: tuple[Function, ...] = (),
    classes: tuple[Class, ...] = (),
) -> Module:
    """Create a valid Module for tests."""
    return Module(
        name=name,
        path=Path(f"{name.replace('.', '/')}.py"),
        imports=(),
        classes=classes,
        functions=functions,
        constants=(),
    )


def make_codebase(*modules: Module, root_package: str = "myapp") -> Codebase:
    """Create a Codebase with given modules."""
    codebase = Codebase(root_path=Path("/test"), root_package=root_package)
    for module in modules:
        codebase.add_module(module)
    return codebase


class TestArchCheckFunctions:
    """Tests for ArchCheck.functions()."""

    def test_functions_returns_query(self) -> None:
        """functions() returns FunctionQuery."""
        codebase = make_codebase()
        arch = ArchCheck(codebase)
        result = arch.functions()
        assert isinstance(result, FunctionQuery)

    def test_functions_query_can_execute(self) -> None:
        """functions() query can execute and return functions."""
        f1 = make_function("foo", "myapp.domain.foo")
        f2 = make_function("bar", "myapp.infra.bar")
        m1 = make_module("myapp.domain", functions=(f1,))
        m2 = make_module("myapp.infra", functions=(f2,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        functions = arch.functions().execute()

        assert len(functions) == 2


class TestFunctionQueryFilters:
    """Tests for FunctionQuery filter methods."""

    def test_in_layer_filters(self) -> None:
        """in_layer() filters by layer name."""
        f_domain = make_function("foo", "myapp.domain.foo")
        f_infra = make_function("bar", "myapp.infrastructure.bar")
        m1 = make_module("myapp.domain", functions=(f_domain,))
        m2 = make_module("myapp.infrastructure", functions=(f_infra,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        result = arch.functions().in_layer("domain").execute()

        assert len(result) == 1
        assert result[0] is f_domain

    def test_in_module_filters(self) -> None:
        """in_module() filters by module pattern."""
        f1 = make_function("foo", "myapp.domain.user.foo")
        f2 = make_function("bar", "myapp.domain.order.bar")
        f3 = make_function("baz", "myapp.infra.baz")
        m1 = make_module("myapp.domain.user", functions=(f1,))
        m2 = make_module("myapp.domain.order", functions=(f2,))
        m3 = make_module("myapp.infra", functions=(f3,))
        codebase = make_codebase(m1, m2, m3)
        arch = ArchCheck(codebase)

        result = arch.functions().in_module("myapp.domain.**").execute()

        assert len(result) == 2
        assert f1 in result
        assert f2 in result

    def test_matching_filters_by_qualified_name(self) -> None:
        """matching() filters by qualified name pattern."""
        f1 = make_function("get_user", "myapp.domain.get_user")
        f2 = make_function("get_order", "myapp.domain.get_order")
        f3 = make_function("save", "myapp.domain.save")
        m = make_module("myapp.domain", functions=(f1, f2, f3))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        result = arch.functions().matching("**.get_*").execute()

        assert len(result) == 2
        assert f1 in result
        assert f2 in result

    def test_named_filters_by_function_name(self) -> None:
        """named() filters by function name pattern."""
        f1 = make_function("test_foo", "myapp.test_foo")
        f2 = make_function("test_bar", "myapp.test_bar")
        f3 = make_function("helper", "myapp.helper")
        m = make_module("myapp", functions=(f1, f2, f3))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        result = arch.functions().named("test_*").execute()

        assert len(result) == 2
        assert f1 in result
        assert f2 in result

    def test_async_only_filters(self) -> None:
        """async_only() filters to async functions."""
        f_sync = make_function("sync_func", "myapp.sync_func", is_async=False)
        f_async = make_function("async_func", "myapp.async_func", is_async=True)
        m = make_module("myapp", functions=(f_sync, f_async))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        result = arch.functions().async_only().execute()

        assert len(result) == 1
        assert result[0] is f_async

    def test_methods_only_filters(self) -> None:
        """methods_only() filters to methods."""
        f_func = make_function("func", "myapp.func", is_method=False)
        m_method = make_function("method", "myapp.Cls.method", is_method=True)
        cls = make_class("Cls", "myapp.Cls", methods=(m_method,))
        m = make_module("myapp", functions=(f_func,), classes=(cls,))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        result = arch.functions().methods_only().execute()

        assert len(result) == 1
        assert result[0] is m_method

    def test_module_level_only_filters(self) -> None:
        """module_level_only() filters to module-level functions."""
        f_func = make_function("func", "myapp.func", is_method=False)
        m_method = make_function("method", "myapp.Cls.method", is_method=True)
        cls = make_class("Cls", "myapp.Cls", methods=(m_method,))
        m = make_module("myapp", functions=(f_func,), classes=(cls,))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        result = arch.functions().module_level_only().execute()

        assert len(result) == 1
        assert result[0] is f_func

    def test_that_filters_by_predicate(self) -> None:
        """that() filters by custom predicate."""
        f1 = make_function("foo", "myapp.foo")
        f2 = make_function("bar", "myapp.bar")
        m = make_module("myapp", functions=(f1, f2))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        result = arch.functions().that(lambda f: "foo" in f.name).execute()

        assert len(result) == 1
        assert result[0] is f1

    def test_chained_filters(self) -> None:
        """Multiple filters can be chained."""
        f1 = make_function("async_handler", "myapp.handlers.async_handler", is_async=True)
        f2 = make_function("sync_handler", "myapp.handlers.sync_handler", is_async=False)
        f3 = make_function("async_util", "myapp.utils.async_util", is_async=True)
        m1 = make_module("myapp.handlers", functions=(f1, f2))
        m2 = make_module("myapp.utils", functions=(f3,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        result = (
            arch.functions()
            .in_layer("handlers")
            .async_only()
            .execute()
        )

        assert len(result) == 1
        assert result[0] is f1


class TestFunctionQueryShould:
    """Tests for FunctionQuery.should() transition."""

    def test_should_returns_assertion(self) -> None:
        """should() returns FunctionAssertion."""
        f = make_function("foo", "myapp.foo")
        m = make_module("myapp", functions=(f,))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        result = arch.functions().should()

        assert isinstance(result, FunctionAssertion)

    def test_should_passes_filtered_functions(self) -> None:
        """should() passes filtered functions to assertion."""
        f1 = make_function("foo", "myapp.domain.foo")
        f2 = make_function("bar", "myapp.infra.bar")
        m1 = make_module("myapp.domain", functions=(f1,))
        m2 = make_module("myapp.infra", functions=(f2,))
        codebase = make_codebase(m1, m2)
        arch = ArchCheck(codebase)

        assertion = arch.functions().in_layer("domain").should()

        assert assertion.function_count == 1


class TestFunctionAssertionNotCall:
    """Tests for FunctionAssertion.not_call()."""

    def test_no_patterns_raises(self) -> None:
        """not_call() with no patterns raises ValueError."""
        assertion = FunctionAssertion(_functions=())
        with pytest.raises(ValueError, match="at least one pattern required"):
            assertion.not_call()

    def test_no_violation_when_no_forbidden_calls(self) -> None:
        """No violation when function doesn't call forbidden."""
        f = make_function(
            "foo",
            "myapp.foo",
            body_calls=(make_call_info("allowed_func"),),
        )
        assertion = FunctionAssertion(_functions=(f,))

        violations = assertion.not_call("forbidden_*").collect()

        assert len(violations) == 0

    def test_violation_when_calls_forbidden(self) -> None:
        """Violation when function calls forbidden pattern."""
        f = make_function(
            "foo",
            "myapp.foo",
            body_calls=(make_call_info("forbidden_func", "myapp.forbidden_func"),),
        )
        assertion = FunctionAssertion(_functions=(f,))

        violations = assertion.not_call("**.forbidden_*").collect()

        assert len(violations) == 1
        assert "no_call" in violations[0].rule_name


class TestFunctionAssertionOnlyCall:
    """Tests for FunctionAssertion.only_call()."""

    def test_no_patterns_raises(self) -> None:
        """only_call() with no patterns raises ValueError."""
        assertion = FunctionAssertion(_functions=())
        with pytest.raises(ValueError, match="at least one pattern required"):
            assertion.only_call()

    def test_no_violation_when_all_calls_allowed(self) -> None:
        """No violation when all calls are allowed."""
        f = make_function(
            "foo",
            "myapp.foo",
            body_calls=(
                make_call_info("allowed", "myapp.helpers.allowed"),
            ),
        )
        assertion = FunctionAssertion(_functions=(f,))

        violations = assertion.only_call("myapp.helpers.**").collect()

        assert len(violations) == 0

    def test_violation_when_calls_non_allowed(self) -> None:
        """Violation when function calls non-allowed."""
        f = make_function(
            "foo",
            "myapp.foo",
            body_calls=(make_call_info("forbidden", "external.forbidden"),),
        )
        assertion = FunctionAssertion(_functions=(f,))

        violations = assertion.only_call("myapp.**").collect()

        assert len(violations) == 1
        assert "only_call" in violations[0].rule_name


class TestFunctionAssertionBeInLayer:
    """Tests for FunctionAssertion.be_in_layer()."""

    def test_no_violation_when_in_layer(self) -> None:
        """No violation when function is in expected layer."""
        f = make_function("foo", "myapp.domain.foo")
        assertion = FunctionAssertion(_functions=(f,))

        violations = assertion.be_in_layer("domain").collect()

        assert len(violations) == 0

    def test_violation_when_not_in_layer(self) -> None:
        """Violation when function is not in expected layer."""
        f = make_function("foo", "myapp.infrastructure.foo")
        assertion = FunctionAssertion(_functions=(f,))

        violations = assertion.be_in_layer("domain").collect()

        assert len(violations) == 1
        assert "be_in_layer" in violations[0].rule_name


class TestFunctionAssertionExecution:
    """Tests for FunctionAssertion execution methods."""

    def test_assert_check_raises_on_violations(self) -> None:
        """assert_check() raises ArchitectureViolationError on violations."""
        f = make_function("foo", "myapp.infra.foo")
        assertion = FunctionAssertion(_functions=(f,))

        with pytest.raises(ArchitectureViolationError):
            assertion.be_in_layer("domain").assert_check()

    def test_assert_check_passes_on_no_violations(self) -> None:
        """assert_check() does not raise when no violations."""
        f = make_function("foo", "myapp.domain.foo")
        assertion = FunctionAssertion(_functions=(f,))

        # Should not raise
        assertion.be_in_layer("domain").assert_check()

    def test_is_valid_true_on_no_violations(self) -> None:
        """is_valid() returns True when no violations."""
        f = make_function("foo", "myapp.domain.foo")
        assertion = FunctionAssertion(_functions=(f,))

        assert assertion.be_in_layer("domain").is_valid()

    def test_is_valid_false_on_violations(self) -> None:
        """is_valid() returns False when violations exist."""
        f = make_function("foo", "myapp.infra.foo")
        assertion = FunctionAssertion(_functions=(f,))

        assert not assertion.be_in_layer("domain").is_valid()


class TestFunctionFluentChaining:
    """Tests for full fluent chain with functions."""

    def test_full_chain_pass(self) -> None:
        """Full fluent chain passes with valid architecture."""
        f = make_function(
            "handler",
            "myapp.handlers.handler",
            is_async=True,
            body_calls=(make_call_info("helper", "myapp.helpers.helper"),),
        )
        m = make_module("myapp.handlers", functions=(f,))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        # Should not raise
        (
            arch.functions()
            .in_layer("handlers")
            .async_only()
            .should()
            .not_call("external.**")
            .assert_check()
        )

    def test_full_chain_fail(self) -> None:
        """Full fluent chain fails with invalid architecture."""
        f = make_function(
            "handler",
            "myapp.handlers.handler",
            body_calls=(make_call_info("external", "external.api"),),
        )
        m = make_module("myapp.handlers", functions=(f,))
        codebase = make_codebase(m)
        arch = ArchCheck(codebase)

        with pytest.raises(ArchitectureViolationError):
            (
                arch.functions()
                .should()
                .not_call("external.**")
                .assert_check()
            )
