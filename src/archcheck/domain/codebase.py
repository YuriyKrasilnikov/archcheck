"""Domain layer: codebase model for static analysis.

Immutable value objects representing Python source structure.
FAIL-FIRST: invalid input raises immediately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from archcheck.domain.exceptions import InvalidImportLevelError, ModuleNameMismatchError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from archcheck.domain.events import Location


@dataclass(frozen=True, slots=True)
class Import:
    """Python import statement.

    Represents both absolute and relative imports.

    Examples:
        import typing             → Import("typing", None, None, False, 0)
        from typing import Optional → Import("typing", "Optional", None, False, 0)
        from . import foo         → Import("", "foo", None, True, 1)
        from ..sub import bar     → Import("sub", "bar", None, True, 2)

    Invariants (FAIL-FIRST):
        - level >= 0
        - is_relative implies level > 0
        - not is_relative implies level == 0
    """

    module: str
    name: str | None
    alias: str | None
    is_relative: bool
    level: int

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST on invalid state."""
        if self.level < 0:
            raise InvalidImportLevelError(self.level, "level must be >= 0")
        if self.is_relative and self.level == 0:
            raise InvalidImportLevelError(self.level, "relative import requires level > 0")
        if not self.is_relative and self.level > 0:
            raise InvalidImportLevelError(self.level, "absolute import requires level == 0")


class ParameterKind(Enum):
    """Python function parameter kind.

    Maps to inspect.Parameter.kind values.
    """

    POSITIONAL_ONLY = "POSITIONAL_ONLY"
    POSITIONAL_OR_KEYWORD = "POSITIONAL_OR_KEYWORD"
    VAR_POSITIONAL = "VAR_POSITIONAL"
    KEYWORD_ONLY = "KEYWORD_ONLY"
    VAR_KEYWORD = "VAR_KEYWORD"


@dataclass(frozen=True, slots=True)
class Parameter:
    """Function parameter.

    Represents a single parameter in a function signature.
    Name stored without asterisks (e.g., "args" not "*args").

    Examples:
        def f(x: int = 0)     → Parameter("x", "int", "0", POSITIONAL_OR_KEYWORD)
        def f(x, /)           → Parameter("x", None, None, POSITIONAL_ONLY)
        def f(*args)          → Parameter("args", None, None, VAR_POSITIONAL)
        def f(*, x)           → Parameter("x", None, None, KEYWORD_ONLY)
        def f(**kwargs)       → Parameter("kwargs", None, None, VAR_KEYWORD)
    """

    name: str
    annotation: str | None
    default: str | None
    kind: ParameterKind


@dataclass(frozen=True, slots=True)
class Function:
    """Python function or method.

    Represents function definition from AST.
    Location reused from events.py (DRY).

    body_calls contains unresolved names as seen in AST.
    Resolution to FQN happens in call_resolver.

    Examples:
        def foo(): pass           → Function("foo", "mod.foo", ...)
        async def fetch(): ...    → Function("fetch", ..., is_async=True)
        def f(): yield x          → Function("f", ..., is_generator=True)
        class C:
            def m(self): ...      → Function("m", "mod.C.m", ..., is_method=True)
    """

    name: str
    qualified_name: str
    parameters: tuple[Parameter, ...]
    return_annotation: str | None
    location: Location
    is_async: bool
    is_generator: bool
    is_method: bool
    decorators: tuple[str, ...]
    body_calls: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Class:
    """Python class definition.

    Represents class from AST with methods and metadata.

    Examples:
        class Foo: pass                → Class("Foo", "mod.Foo", ...)
        class User(BaseModel): ...     → Class("User", ..., bases=("BaseModel",))
        class Repo(Protocol): ...      → Class("Repo", ..., is_protocol=True)
        @dataclass
        class DTO: ...                 → Class("DTO", ..., is_dataclass=True)
    """

    name: str
    qualified_name: str
    bases: tuple[str, ...]
    methods: tuple[Function, ...]
    location: Location
    is_protocol: bool
    is_dataclass: bool


@dataclass(frozen=True, slots=True)
class Module:
    """Python module (single .py file).

    Represents parsed module with all imports, classes, and functions.

    Examples:
        src/app/utils.py  → Module("app.utils", Path(...), ...)
        src/app/__init__.py → Module("app", Path(...), ...)
    """

    name: str
    path: Path
    imports: tuple[Import, ...]
    classes: tuple[Class, ...]
    functions: tuple[Function, ...]
    docstring: str | None


@dataclass(frozen=True, slots=True)
class Codebase:
    """Collection of modules representing a Python project.

    Invariants (FAIL-FIRST):
        - For each (key, module) in modules: key == module.name

    Provides Codebase.empty() classmethod for tests/empty merge.
    """

    root_path: Path
    root_package: str
    modules: Mapping[str, Module] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate invariants. FAIL-FIRST on name/key mismatch."""
        for key, module in self.modules.items():
            if key != module.name:
                raise ModuleNameMismatchError(key, module.name)

    @classmethod
    def empty(cls) -> Codebase:
        """Create empty codebase for tests or empty runtime merge."""
        return cls(root_path=Path(), root_package="", modules={})
