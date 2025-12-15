"""Tests for domain/model/enums.py."""

from archcheck.domain.model.enums import RuleCategory, Severity, Visibility


class TestVisibility:
    """Tests for Visibility enum."""

    def test_public_exists(self) -> None:
        assert Visibility.PUBLIC is not None

    def test_protected_exists(self) -> None:
        assert Visibility.PROTECTED is not None

    def test_private_exists(self) -> None:
        assert Visibility.PRIVATE is not None

    def test_all_values_unique(self) -> None:
        values = [v.value for v in Visibility]
        assert len(values) == len(set(values))

    def test_has_three_members(self) -> None:
        assert len(Visibility) == 3


class TestSeverity:
    """Tests for Severity enum."""

    def test_error_exists(self) -> None:
        assert Severity.ERROR is not None

    def test_warning_exists(self) -> None:
        assert Severity.WARNING is not None

    def test_info_exists(self) -> None:
        assert Severity.INFO is not None

    def test_all_values_unique(self) -> None:
        values = [v.value for v in Severity]
        assert len(values) == len(set(values))

    def test_has_three_members(self) -> None:
        assert len(Severity) == 3


class TestRuleCategory:
    """Tests for RuleCategory enum."""

    def test_import_exists(self) -> None:
        assert RuleCategory.IMPORT is not None

    def test_naming_exists(self) -> None:
        assert RuleCategory.NAMING is not None

    def test_inheritance_exists(self) -> None:
        assert RuleCategory.INHERITANCE is not None

    def test_decorator_exists(self) -> None:
        assert RuleCategory.DECORATOR is not None

    def test_purity_exists(self) -> None:
        assert RuleCategory.PURITY is not None

    def test_di_exists(self) -> None:
        assert RuleCategory.DI is not None

    def test_fail_first_exists(self) -> None:
        assert RuleCategory.FAIL_FIRST is not None

    def test_custom_exists(self) -> None:
        assert RuleCategory.CUSTOM is not None

    def test_all_values_unique(self) -> None:
        values = [v.value for v in RuleCategory]
        assert len(values) == len(set(values))

    def test_has_fifteen_members(self) -> None:
        # IMPORT, NAMING, INHERITANCE, DECORATOR, PURITY, DI, FAIL_FIRST,
        # BOUNDARIES, COUPLING, COHESION, ISOLATION, CONTRACTS, QUALITY, RUNTIME, CUSTOM
        assert len(RuleCategory) == 15
