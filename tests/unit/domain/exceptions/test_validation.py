"""Tests for domain/exceptions/validation.py."""

import pytest

from archcheck.domain.exceptions.base import ArchCheckError
from archcheck.domain.exceptions.validation import RuleValidationError


class TestRuleValidationError:
    """Tests for RuleValidationError exception."""

    def test_is_archcheck_error(self) -> None:
        assert issubclass(RuleValidationError, ArchCheckError)

    def test_has_rule_name_attribute(self) -> None:
        err = RuleValidationError("no-forbidden-import", "pattern is invalid")
        assert err.rule_name == "no-forbidden-import"

    def test_has_reason_attribute(self) -> None:
        err = RuleValidationError("no-forbidden-import", "pattern is invalid")
        assert err.reason == "pattern is invalid"

    def test_message_format(self) -> None:
        err = RuleValidationError("layer-check", "unknown layer 'foo'")
        assert str(err) == "Invalid rule 'layer-check': unknown layer 'foo'"

    def test_can_catch_as_archcheck_error(self) -> None:
        with pytest.raises(ArchCheckError) as exc_info:
            raise RuleValidationError("rule", "reason")
        assert isinstance(exc_info.value, RuleValidationError)
