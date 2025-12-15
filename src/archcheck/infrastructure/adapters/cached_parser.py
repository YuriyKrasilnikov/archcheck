"""Cached source parser adapter.

Decorator pattern: wraps SourceParserPort with content-hash based caching.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from archcheck.domain.model.codebase import Codebase
from archcheck.domain.model.module import Module
from archcheck.domain.ports.source_parser import SourceParserPort


@dataclass
class CachedSourceParser(SourceParserPort):
    """Parser with content-hash based caching.

    Decorator pattern: wraps another SourceParserPort.
    Uses SHA-256 hash of file content for cache invalidation.

    Cache is in-memory only - no persistence between runs.
    Thread-safe for read operations, not for write operations.

    Attributes:
        _inner: Wrapped parser implementation
        _cache: Path → (content_hash, Module) mapping
    """

    _inner: SourceParserPort
    _cache: dict[Path, tuple[str, Module]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST."""
        if self._inner is None:
            raise TypeError("_inner parser must not be None")

    def parse_file(self, path: Path) -> Module:
        """Parse with cache lookup.

        Cache hit: return cached Module if content hash matches.
        Cache miss: parse with inner parser, cache result.

        Args:
            path: Path to .py file

        Returns:
            Parsed Module (cached or fresh)

        Raises:
            ParsingError: If file cannot be read or parsed
        """
        # Read content for hash
        content = path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check cache
        if path in self._cache:
            cached_hash, cached_module = self._cache[path]
            if cached_hash == content_hash:
                return cached_module

        # Cache miss - parse and cache
        module = self._inner.parse_file(path)
        self._cache[path] = (content_hash, module)
        return module

    def parse_directory(self, path: Path, package_name: str) -> Codebase:
        """Parse directory (delegates to inner parser).

        Individual files are cached via parse_file().

        Args:
            path: Root directory path
            package_name: Root package name

        Returns:
            Codebase with all modules and graphs
        """
        return self._inner.parse_directory(path, package_name)

    def invalidate(self, path: Path) -> None:
        """Explicitly invalidate cache entry.

        Use when you know a file has changed externally.

        Args:
            path: Path to invalidate
        """
        self._cache.pop(path, None)

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Number of cached modules."""
        return len(self._cache)

    @property
    def cache_hit_paths(self) -> frozenset[Path]:
        """Paths currently in cache."""
        return frozenset(self._cache.keys())
