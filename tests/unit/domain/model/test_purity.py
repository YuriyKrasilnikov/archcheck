"""Tests for domain/model/purity.py."""

import pytest

from archcheck.domain.model.purity import PurityInfo


class TestPurityInfoCreation:
    """Tests for valid PurityInfo creation."""

    def test_pure_function(self) -> None:
        info = PurityInfo(is_pure=True)
        assert info.is_pure is True
        assert info.has_io_calls is False
        assert info.has_random is False
        assert info.has_time is False
        assert info.has_env_access is False
        assert info.has_global_mutation is False
        assert info.has_argument_mutation is False
        assert info.has_external_state is False
        assert info.violations == ()

    def test_impure_with_io(self) -> None:
        info = PurityInfo(is_pure=False, has_io_calls=True)
        assert info.is_pure is False
        assert info.has_io_calls is True

    def test_impure_with_random(self) -> None:
        info = PurityInfo(is_pure=False, has_random=True)
        assert info.is_pure is False
        assert info.has_random is True

    def test_impure_with_time(self) -> None:
        info = PurityInfo(is_pure=False, has_time=True)
        assert info.has_time is True

    def test_impure_with_env_access(self) -> None:
        info = PurityInfo(is_pure=False, has_env_access=True)
        assert info.has_env_access is True

    def test_impure_with_global_mutation(self) -> None:
        info = PurityInfo(is_pure=False, has_global_mutation=True)
        assert info.has_global_mutation is True

    def test_impure_with_argument_mutation(self) -> None:
        info = PurityInfo(is_pure=False, has_argument_mutation=True)
        assert info.has_argument_mutation is True

    def test_impure_with_external_state(self) -> None:
        info = PurityInfo(is_pure=False, has_external_state=True)
        assert info.has_external_state is True

    def test_impure_with_violations(self) -> None:
        info = PurityInfo(is_pure=False, violations=("calls print()",))
        assert info.violations == ("calls print()",)

    def test_impure_with_multiple_flags(self) -> None:
        info = PurityInfo(
            is_pure=False,
            has_io_calls=True,
            has_random=True,
            has_time=True,
        )
        assert info.has_io_calls is True
        assert info.has_random is True
        assert info.has_time is True

    def test_is_frozen(self) -> None:
        info = PurityInfo(is_pure=True)
        with pytest.raises(AttributeError):
            info.is_pure = False  # type: ignore[misc]


class TestPurityInfoFailFirst:
    """Tests for FAIL-FIRST validation in PurityInfo."""

    def test_pure_with_io_raises(self) -> None:
        with pytest.raises(ValueError, match="is_pure=True contradicts impurity flags"):
            PurityInfo(is_pure=True, has_io_calls=True)

    def test_pure_with_random_raises(self) -> None:
        with pytest.raises(ValueError, match="is_pure=True contradicts impurity flags"):
            PurityInfo(is_pure=True, has_random=True)

    def test_pure_with_time_raises(self) -> None:
        with pytest.raises(ValueError, match="is_pure=True contradicts impurity flags"):
            PurityInfo(is_pure=True, has_time=True)

    def test_pure_with_env_raises(self) -> None:
        with pytest.raises(ValueError, match="is_pure=True contradicts impurity flags"):
            PurityInfo(is_pure=True, has_env_access=True)

    def test_pure_with_global_mutation_raises(self) -> None:
        with pytest.raises(ValueError, match="is_pure=True contradicts impurity flags"):
            PurityInfo(is_pure=True, has_global_mutation=True)

    def test_pure_with_argument_mutation_raises(self) -> None:
        with pytest.raises(ValueError, match="is_pure=True contradicts impurity flags"):
            PurityInfo(is_pure=True, has_argument_mutation=True)

    def test_pure_with_external_state_raises(self) -> None:
        with pytest.raises(ValueError, match="is_pure=True contradicts impurity flags"):
            PurityInfo(is_pure=True, has_external_state=True)

    def test_impure_without_flags_or_violations_raises(self) -> None:
        with pytest.raises(
            ValueError, match="is_pure=False requires at least one impurity flag or violation"
        ):
            PurityInfo(is_pure=False)

    def test_pure_with_multiple_flags_raises(self) -> None:
        with pytest.raises(ValueError, match="is_pure=True contradicts impurity flags"):
            PurityInfo(
                is_pure=True,
                has_io_calls=True,
                has_random=True,
            )
