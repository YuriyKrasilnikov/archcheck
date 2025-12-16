"""Pattern matching for module name filtering.

Glob-like patterns for matching Python module names.

Syntax:
    *    one segment (no dots)
    **   any segments (with dots)
    ?    one character
    .    literal dot

Special cases:
    foo.**   matches foo AND all children (foo, foo.bar, foo.bar.baz)
    **.foo   matches foo AND any prefix (foo, bar.foo, bar.baz.foo)
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompiledPattern:
    """Compiled module name pattern.

    Immutable value object containing original pattern and compiled regex.

    Attributes:
        original: Original pattern string
        regex: Compiled regex for matching
    """

    original: str
    regex: re.Pattern[str]

    def match(self, name: str) -> bool:
        """Check if name matches pattern.

        Args:
            name: Module name to match

        Returns:
            True if name matches pattern

        Raises:
            TypeError: If name is None
        """
        if name is None:
            raise TypeError("name must not be None")
        return self.regex.match(name) is not None

    def __str__(self) -> str:
        """Return original pattern string."""
        return self.original

    def __repr__(self) -> str:
        """Return repr with original pattern."""
        return f"CompiledPattern({self.original!r})"


def compile_pattern(pattern: str) -> CompiledPattern:
    """Compile glob pattern to regex.

    FAIL-FIRST: raises ValueError for invalid patterns.

    Syntax:
        *    matches one segment (no dots): [^.]+
        **   matches any segments (with dots): .*
        ?    matches one character: .
        .    matches literal dot: \\.

    Special cases:
        foo.**   = foo OR foo.* (trailing .** includes parent)
        **.foo   = foo OR *.foo (leading **. includes target)

    Args:
        pattern: Glob pattern string

    Returns:
        CompiledPattern with original and compiled regex

    Raises:
        ValueError: If pattern is empty
    """
    if not pattern:
        raise ValueError("pattern must not be empty")

    # Handle pure ** (matches anything)
    if pattern == "**":
        return CompiledPattern(original=pattern, regex=re.compile(r"^.*$"))

    # Escape all regex special characters
    escaped = re.escape(pattern)

    # Escaped sequences lengths:
    # \.\*\* = 6 chars (dot + double star)
    # \*\*\. = 6 chars (double star + dot)
    # \*\* = 4 chars (double star alone)

    # Process special cases BEFORE general replacements
    # Trailing .** = this module AND children: foo(\..*)?
    if escaped.endswith(r"\.\*\*"):
        escaped = escaped[:-6] + r"(\..*)?$"
    else:
        escaped += "$"

    # Leading **. = any prefix AND target: (.*\.)?foo
    if escaped.startswith(r"\*\*\."):
        escaped = r"^(.*\.)?" + escaped[6:]  # Skip 6 chars: \*\*\.
    else:
        escaped = "^" + escaped

    # Middle .**. = zero or more segments with dots: (\..*)?\.
    # Must do this BEFORE general ** replacement
    escaped = escaped.replace(r"\.\*\*\.", r"(\..*)?\.")

    # Replace remaining ** (middle of pattern) → .*
    escaped = escaped.replace(r"\*\*", r".*")

    # Replace * → one segment (no dots)
    escaped = escaped.replace(r"\*", r"[^.]+")

    # Replace ? → one character
    escaped = escaped.replace(r"\?", r".")

    try:
        regex = re.compile(escaped)
    except re.error as e:
        raise ValueError(f"invalid pattern '{pattern}': {e}") from e

    return CompiledPattern(original=pattern, regex=regex)


def matches_any(name: str, patterns: tuple[CompiledPattern, ...]) -> bool:
    """Check if name matches any of the patterns.

    Args:
        name: Module name to match
        patterns: Compiled patterns to check

    Returns:
        True if name matches at least one pattern
    """
    return any(p.match(name) for p in patterns)


def matches_all(name: str, patterns: tuple[CompiledPattern, ...]) -> bool:
    """Check if name matches all patterns.

    Args:
        name: Module name to match
        patterns: Compiled patterns to check

    Returns:
        True if name matches all patterns (empty patterns = True)
    """
    return all(p.match(name) for p in patterns)
