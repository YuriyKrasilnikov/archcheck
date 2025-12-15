"""Reporters for architecture check results.

Built-in reporters use stdlib only.
Users can implement custom reporters (e.g., RichReporter).
"""

from archcheck.application.reporters._base import BaseReporter
from archcheck.application.reporters.json_reporter import JSONReporter
from archcheck.application.reporters.plain_text import PlainTextReporter

__all__ = [
    "BaseReporter",
    "PlainTextReporter",
    "JSONReporter",
]
