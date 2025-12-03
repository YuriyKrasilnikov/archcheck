"""pytest plugin for archcheck."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest plugin."""
    config.addinivalue_line(
        "markers",
        "archcheck: mark test as architecture test",
    )
