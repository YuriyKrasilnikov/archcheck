"""Tests for infrastructure/analyzers/context.py."""

import pytest

from archcheck.infrastructure.analyzers.context import (
    AnalysisContext,
    ContextFrame,
    ContextType,
)


class TestContextType:
    """Tests for ContextType enum."""

    def test_all_types_exist(self) -> None:
        assert ContextType.MODULE
        assert ContextType.CLASS
        assert ContextType.FUNCTION
        assert ContextType.TYPE_CHECKING
        assert ContextType.CONDITIONAL
        assert ContextType.LOOP
        assert ContextType.COMPREHENSION


class TestContextFrame:
    """Tests for ContextFrame dataclass."""

    def test_with_type_only(self) -> None:
        frame = ContextFrame(type=ContextType.MODULE)
        assert frame.type == ContextType.MODULE
        assert frame.name is None

    def test_with_name(self) -> None:
        frame = ContextFrame(type=ContextType.FUNCTION, name="foo")
        assert frame.type == ContextType.FUNCTION
        assert frame.name == "foo"


class TestAnalysisContextCreation:
    """Tests for AnalysisContext creation."""

    def test_empty_context(self) -> None:
        ctx = AnalysisContext()
        assert ctx.depth == 0
        assert ctx.is_empty is True
        assert ctx.in_type_checking is False
        assert ctx.in_function is False
        assert ctx.in_conditional is False
        assert ctx.in_class is False
        assert ctx.in_loop is False
        assert ctx.in_comprehension is False
        assert ctx.current_class is None
        assert ctx.current_function is None


class TestAnalysisContextPushPop:
    """Tests for push/pop operations."""

    def test_push_module(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.MODULE)
        assert ctx.depth == 1
        assert ctx.is_empty is False

    def test_push_pop_returns_frame(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.FUNCTION, "my_func")
        frame = ctx.pop()
        assert frame.type == ContextType.FUNCTION
        assert frame.name == "my_func"
        assert ctx.is_empty is True

    def test_pop_empty_raises(self) -> None:
        ctx = AnalysisContext()
        with pytest.raises(IndexError, match="cannot pop from empty"):
            ctx.pop()

    def test_push_empty_name_raises(self) -> None:
        ctx = AnalysisContext()
        with pytest.raises(ValueError, match="context name must be non-empty string or None"):
            ctx.push(ContextType.FUNCTION, "")


class TestAnalysisContextTypeChecking:
    """Tests for TYPE_CHECKING tracking."""

    def test_in_type_checking_after_push(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.TYPE_CHECKING)
        assert ctx.in_type_checking is True

    def test_not_in_type_checking_after_pop(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.TYPE_CHECKING)
        ctx.pop()
        assert ctx.in_type_checking is False

    def test_nested_type_checking(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.TYPE_CHECKING)
        ctx.push(ContextType.TYPE_CHECKING)
        assert ctx.in_type_checking is True
        ctx.pop()
        assert ctx.in_type_checking is True
        ctx.pop()
        assert ctx.in_type_checking is False


class TestAnalysisContextFunction:
    """Tests for function tracking."""

    def test_in_function_after_push(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.FUNCTION, "foo")
        assert ctx.in_function is True
        assert ctx.current_function == "foo"

    def test_nested_functions(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.FUNCTION, "outer")
        ctx.push(ContextType.FUNCTION, "inner")
        assert ctx.current_function == "inner"
        ctx.pop()
        assert ctx.current_function == "outer"


class TestAnalysisContextClass:
    """Tests for class tracking."""

    def test_in_class_after_push(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.CLASS, "MyClass")
        assert ctx.in_class is True
        assert ctx.current_class == "MyClass"

    def test_nested_classes(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.CLASS, "Outer")
        ctx.push(ContextType.CLASS, "Inner")
        assert ctx.current_class == "Inner"
        ctx.pop()
        assert ctx.current_class == "Outer"


class TestAnalysisContextConditional:
    """Tests for conditional tracking."""

    def test_in_conditional_after_push(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.CONDITIONAL)
        assert ctx.in_conditional is True

    def test_nested_conditionals(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.CONDITIONAL)
        ctx.push(ContextType.CONDITIONAL)
        assert ctx.in_conditional is True
        ctx.pop()
        assert ctx.in_conditional is True
        ctx.pop()
        assert ctx.in_conditional is False


class TestAnalysisContextLoop:
    """Tests for loop tracking."""

    def test_in_loop_after_push(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.LOOP)
        assert ctx.in_loop is True

    def test_not_in_loop_after_pop(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.LOOP)
        ctx.pop()
        assert ctx.in_loop is False


class TestAnalysisContextComprehension:
    """Tests for comprehension tracking."""

    def test_in_comprehension_after_push(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.COMPREHENSION)
        assert ctx.in_comprehension is True

    def test_not_in_comprehension_after_pop(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.COMPREHENSION)
        ctx.pop()
        assert ctx.in_comprehension is False


class TestAnalysisContextComplexScenarios:
    """Tests for complex nested scenarios."""

    def test_class_with_method(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.MODULE)
        ctx.push(ContextType.CLASS, "MyClass")
        ctx.push(ContextType.FUNCTION, "my_method")

        assert ctx.in_class is True
        assert ctx.in_function is True
        assert ctx.current_class == "MyClass"
        assert ctx.current_function == "my_method"
        assert ctx.depth == 3

    def test_type_checking_inside_class(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.CLASS, "MyClass")
        ctx.push(ContextType.TYPE_CHECKING)
        ctx.push(ContextType.FUNCTION, "helper")

        assert ctx.in_type_checking is True
        assert ctx.in_class is True
        assert ctx.in_function is True

    def test_full_traversal(self) -> None:
        ctx = AnalysisContext()

        # Enter module
        ctx.push(ContextType.MODULE)
        assert ctx.depth == 1

        # Enter TYPE_CHECKING block
        ctx.push(ContextType.TYPE_CHECKING)
        assert ctx.in_type_checking is True

        # Exit TYPE_CHECKING
        ctx.pop()
        assert ctx.in_type_checking is False

        # Enter class
        ctx.push(ContextType.CLASS, "Parser")

        # Enter method
        ctx.push(ContextType.FUNCTION, "parse")

        # Enter loop
        ctx.push(ContextType.LOOP)

        # Enter conditional
        ctx.push(ContextType.CONDITIONAL)

        assert ctx.depth == 5
        assert ctx.current_class == "Parser"
        assert ctx.current_function == "parse"

        # Pop all
        ctx.pop()  # conditional
        ctx.pop()  # loop
        ctx.pop()  # function
        ctx.pop()  # class
        ctx.pop()  # module

        assert ctx.is_empty is True


class TestAnalysisContextCurrentLookup:
    """Tests for current_class and current_function lookups."""

    def test_current_class_none_when_not_in_class(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.FUNCTION, "foo")
        assert ctx.current_class is None

    def test_current_function_none_when_not_in_function(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.CLASS, "Foo")
        assert ctx.current_function is None

    def test_current_class_finds_nearest(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.CLASS, "Outer")
        ctx.push(ContextType.FUNCTION, "method")
        ctx.push(ContextType.CLASS, "Inner")

        assert ctx.current_class == "Inner"

    def test_current_function_finds_nearest(self) -> None:
        ctx = AnalysisContext()
        ctx.push(ContextType.FUNCTION, "outer")
        ctx.push(ContextType.CLASS, "Local")
        ctx.push(ContextType.FUNCTION, "inner")

        assert ctx.current_function == "inner"
