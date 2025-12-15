"""Tests for domain/model/di.py."""

import pytest

from archcheck.domain.model.di import DIInfo


class TestDIInfoCreation:
    """Tests for valid DIInfo creation."""

    def test_default_values(self) -> None:
        info = DIInfo()
        assert info.has_constructor_injection is False
        assert info.injected_dependencies == ()
        assert info.uses_inject_decorator is False
        assert info.container_registrations == ()

    def test_with_constructor_injection(self) -> None:
        info = DIInfo(
            has_constructor_injection=True,
            injected_dependencies=("UserRepository", "EmailService"),
        )
        assert info.has_constructor_injection is True
        assert info.injected_dependencies == ("UserRepository", "EmailService")

    def test_with_inject_decorator(self) -> None:
        info = DIInfo(uses_inject_decorator=True)
        assert info.uses_inject_decorator is True

    def test_with_container_registrations(self) -> None:
        info = DIInfo(container_registrations=("bind(IService, Service)",))
        assert info.container_registrations == ("bind(IService, Service)",)

    def test_full_di_info(self) -> None:
        info = DIInfo(
            has_constructor_injection=True,
            injected_dependencies=("IRepository",),
            uses_inject_decorator=True,
            container_registrations=("container.register()",),
        )
        assert info.has_constructor_injection is True
        assert info.injected_dependencies == ("IRepository",)
        assert info.uses_inject_decorator is True
        assert info.container_registrations == ("container.register()",)

    def test_is_frozen(self) -> None:
        info = DIInfo()
        with pytest.raises(AttributeError):
            info.has_constructor_injection = True  # type: ignore[misc]


class TestDIInfoFailFirst:
    """Tests for FAIL-FIRST validation in DIInfo."""

    def test_dependencies_without_constructor_injection_raises(self) -> None:
        with pytest.raises(
            ValueError, match="injected_dependencies requires has_constructor_injection=True"
        ):
            DIInfo(
                has_constructor_injection=False,
                injected_dependencies=("Service",),
            )

    def test_dependencies_with_constructor_injection_valid(self) -> None:
        info = DIInfo(
            has_constructor_injection=True,
            injected_dependencies=("Service",),
        )
        assert info.injected_dependencies == ("Service",)
