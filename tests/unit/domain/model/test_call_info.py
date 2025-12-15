"""Tests for CallInfo domain type."""

import pytest

from archcheck.domain.model.call_info import CallInfo
from archcheck.domain.model.call_type import CallType


class TestCallInfoCreation:
    """Test CallInfo creation and validation."""

    def test_create_resolved_call(self) -> None:
        """CallInfo with resolved FQN."""
        call = CallInfo(
            callee_name="func",
            resolved_fqn="myapp.utils.func",
            line=42,
            call_type=CallType.FUNCTION,
        )
        assert call.callee_name == "func"
        assert call.resolved_fqn == "myapp.utils.func"
        assert call.line == 42
        assert call.call_type == CallType.FUNCTION

    def test_create_unresolved_call(self) -> None:
        """CallInfo without resolved FQN."""
        call = CallInfo(
            callee_name="external_func",
            resolved_fqn=None,
            line=10,
            call_type=CallType.FUNCTION,
        )
        assert call.callee_name == "external_func"
        assert call.resolved_fqn is None
        assert call.line == 10

    def test_create_method_call(self) -> None:
        """CallInfo for method call."""
        call = CallInfo(
            callee_name="self.process",
            resolved_fqn="myapp.services.Handler.process",
            line=55,
            call_type=CallType.METHOD,
        )
        assert call.call_type == CallType.METHOD

    def test_create_constructor_call(self) -> None:
        """CallInfo for constructor call."""
        call = CallInfo(
            callee_name="MyClass",
            resolved_fqn="myapp.models.MyClass",
            line=20,
            call_type=CallType.CONSTRUCTOR,
        )
        assert call.call_type == CallType.CONSTRUCTOR

    def test_create_super_call(self) -> None:
        """CallInfo for super() call."""
        call = CallInfo(
            callee_name="super().method",
            resolved_fqn=None,
            line=15,
            call_type=CallType.SUPER,
        )
        assert call.call_type == CallType.SUPER


class TestCallInfoValidation:
    """Test FAIL-FIRST validation."""

    def test_empty_callee_name_fails(self) -> None:
        """Empty callee_name raises ValueError."""
        with pytest.raises(ValueError, match="callee_name must not be empty"):
            CallInfo(
                callee_name="",
                resolved_fqn=None,
                line=1,
                call_type=CallType.FUNCTION,
            )

    def test_zero_line_fails(self) -> None:
        """Line 0 raises ValueError."""
        with pytest.raises(ValueError, match="line must be >= 1"):
            CallInfo(
                callee_name="func",
                resolved_fqn=None,
                line=0,
                call_type=CallType.FUNCTION,
            )

    def test_negative_line_fails(self) -> None:
        """Negative line raises ValueError."""
        with pytest.raises(ValueError, match="line must be >= 1"):
            CallInfo(
                callee_name="func",
                resolved_fqn=None,
                line=-5,
                call_type=CallType.FUNCTION,
            )


class TestCallInfoProperties:
    """Test computed properties."""

    def test_is_resolved_true(self) -> None:
        """is_resolved returns True when FQN is set."""
        call = CallInfo(
            callee_name="func",
            resolved_fqn="myapp.func",
            line=1,
            call_type=CallType.FUNCTION,
        )
        assert call.is_resolved is True

    def test_is_resolved_false(self) -> None:
        """is_resolved returns False when FQN is None."""
        call = CallInfo(
            callee_name="func",
            resolved_fqn=None,
            line=1,
            call_type=CallType.FUNCTION,
        )
        assert call.is_resolved is False

    def test_target_returns_fqn_when_resolved(self) -> None:
        """target returns FQN when available."""
        call = CallInfo(
            callee_name="func",
            resolved_fqn="myapp.func",
            line=1,
            call_type=CallType.FUNCTION,
        )
        assert call.target == "myapp.func"

    def test_target_returns_callee_name_when_unresolved(self) -> None:
        """target returns callee_name when FQN is None."""
        call = CallInfo(
            callee_name="external_func",
            resolved_fqn=None,
            line=1,
            call_type=CallType.FUNCTION,
        )
        assert call.target == "external_func"


class TestCallInfoStr:
    """Test string representation."""

    def test_str_resolved(self) -> None:
        """String format for resolved call."""
        call = CallInfo(
            callee_name="func",
            resolved_fqn="myapp.func",
            line=42,
            call_type=CallType.FUNCTION,
        )
        assert str(call) == "myapp.func:42 (FUNCTION)"

    def test_str_unresolved(self) -> None:
        """String format for unresolved call."""
        call = CallInfo(
            callee_name="unknown",
            resolved_fqn=None,
            line=10,
            call_type=CallType.METHOD,
        )
        assert str(call) == "unknown:10 (METHOD)"


class TestCallInfoImmutability:
    """Test frozen dataclass behavior."""

    def test_cannot_modify_callee_name(self) -> None:
        """Attempting to modify callee_name raises FrozenInstanceError."""
        call = CallInfo(
            callee_name="func",
            resolved_fqn=None,
            line=1,
            call_type=CallType.FUNCTION,
        )
        with pytest.raises(AttributeError):
            call.callee_name = "other"  # type: ignore[misc]

    def test_cannot_modify_line(self) -> None:
        """Attempting to modify line raises FrozenInstanceError."""
        call = CallInfo(
            callee_name="func",
            resolved_fqn=None,
            line=1,
            call_type=CallType.FUNCTION,
        )
        with pytest.raises(AttributeError):
            call.line = 99  # type: ignore[misc]


class TestCallInfoEquality:
    """Test equality and hashing."""

    def test_equal_calls(self) -> None:
        """Identical calls are equal."""
        call1 = CallInfo("func", "myapp.func", 10, CallType.FUNCTION)
        call2 = CallInfo("func", "myapp.func", 10, CallType.FUNCTION)
        assert call1 == call2

    def test_different_callee_name(self) -> None:
        """Different callee_name means not equal."""
        call1 = CallInfo("func1", "myapp.func", 10, CallType.FUNCTION)
        call2 = CallInfo("func2", "myapp.func", 10, CallType.FUNCTION)
        assert call1 != call2

    def test_different_line(self) -> None:
        """Different line means not equal."""
        call1 = CallInfo("func", "myapp.func", 10, CallType.FUNCTION)
        call2 = CallInfo("func", "myapp.func", 20, CallType.FUNCTION)
        assert call1 != call2

    def test_hashable(self) -> None:
        """CallInfo is hashable for use in sets."""
        call = CallInfo("func", "myapp.func", 10, CallType.FUNCTION)
        call_set = {call}
        assert call in call_set

    def test_same_call_same_hash(self) -> None:
        """Equal calls have same hash."""
        call1 = CallInfo("func", "myapp.func", 10, CallType.FUNCTION)
        call2 = CallInfo("func", "myapp.func", 10, CallType.FUNCTION)
        assert hash(call1) == hash(call2)
