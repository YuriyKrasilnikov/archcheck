"""Tests for domain/exceptions/base.py."""

import pytest

from archcheck.domain.exceptions.base import ArchCheckError


class TestArchCheckError:
    """Tests for ArchCheckError base exception."""

    def test_is_exception(self) -> None:
        assert issubclass(ArchCheckError, Exception)

    def test_can_raise_and_catch(self) -> None:
        with pytest.raises(ArchCheckError, match="test message"):
            raise ArchCheckError("test message")

    def test_can_catch_as_exception(self) -> None:
        with pytest.raises(ArchCheckError) as exc_info:
            raise ArchCheckError("test")
        # ArchCheckError is also an Exception
        assert isinstance(exc_info.value, Exception)

    def test_empty_message(self) -> None:
        err = ArchCheckError()
        assert str(err) == ""

    def test_with_args(self) -> None:
        err = ArchCheckError("error", 42, "extra")
        assert err.args == ("error", 42, "extra")
