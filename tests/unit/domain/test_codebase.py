"""Tests for domain/codebase.py.

Tests:
- Import invariants (level >= 0, relative/absolute consistency)
- Import immutability
- Parameter immutability
- Function invariants (qualified_name format)
- Class invariants
- Module invariants
- Codebase invariants (name == key)
"""

from pathlib import Path

import pytest

from archcheck.domain.codebase import (
    Class,
    Codebase,
    Function,
    Import,
    Module,
    Parameter,
    ParameterKind,
)
from archcheck.domain.events import Location


class TestImport:
    """Tests for Import."""

    def test_absolute_import_module(self) -> None:
        """Absolute import: import typing."""
        imp = Import(module="typing", name=None, alias=None, is_relative=False, level=0)

        assert imp.module == "typing"
        assert imp.name is None
        assert imp.alias is None
        assert imp.is_relative is False
        assert imp.level == 0

    def test_absolute_import_from(self) -> None:
        """Absolute from import: from typing import Optional."""
        imp = Import(module="typing", name="Optional", alias=None, is_relative=False, level=0)

        assert imp.module == "typing"
        assert imp.name == "Optional"
        assert imp.alias is None

    def test_absolute_import_alias(self) -> None:
        """Aliased import: from typing import Optional as Opt."""
        imp = Import(module="typing", name="Optional", alias="Opt", is_relative=False, level=0)

        assert imp.name == "Optional"
        assert imp.alias == "Opt"

    def test_relative_import_current(self) -> None:
        """Relative import from current: from . import foo."""
        imp = Import(module="", name="foo", alias=None, is_relative=True, level=1)

        assert imp.module == ""
        assert imp.name == "foo"
        assert imp.is_relative is True
        assert imp.level == 1

    def test_relative_import_parent(self) -> None:
        """Relative import from parent: from .. import bar."""
        imp = Import(module="", name="bar", alias=None, is_relative=True, level=2)

        assert imp.level == 2

    def test_relative_import_submodule(self) -> None:
        """Relative import submodule: from .sub import baz."""
        imp = Import(module="sub", name="baz", alias=None, is_relative=True, level=1)

        assert imp.module == "sub"
        assert imp.name == "baz"
        assert imp.level == 1

    def test_negative_level_raises(self) -> None:
        """Negative level raises ValueError (FAIL-FIRST)."""
        with pytest.raises(ValueError, match="level must be >= 0"):
            Import(module="typing", name=None, alias=None, is_relative=False, level=-1)

    def test_relative_zero_level_raises(self) -> None:
        """Relative import with level=0 raises ValueError (FAIL-FIRST)."""
        with pytest.raises(ValueError, match="relative import requires level > 0"):
            Import(module="", name="foo", alias=None, is_relative=True, level=0)

    def test_absolute_nonzero_level_raises(self) -> None:
        """Absolute import with level>0 raises ValueError (FAIL-FIRST)."""
        with pytest.raises(ValueError, match="absolute import requires level == 0"):
            Import(module="typing", name=None, alias=None, is_relative=False, level=1)

    def test_frozen_immutable(self) -> None:
        """Import is frozen (immutable)."""
        imp = Import(module="typing", name=None, alias=None, is_relative=False, level=0)

        with pytest.raises(AttributeError):
            imp.module = "os"  # type: ignore[misc]

    def test_hashable(self) -> None:
        """Import is hashable (can be used in frozenset)."""
        imp = Import(module="typing", name="Optional", alias=None, is_relative=False, level=0)

        imp_set = frozenset({imp})
        assert imp in imp_set

    def test_equality(self) -> None:
        """Import equality based on all fields."""
        imp1 = Import(module="typing", name="Optional", alias=None, is_relative=False, level=0)
        imp2 = Import(module="typing", name="Optional", alias=None, is_relative=False, level=0)
        imp3 = Import(module="typing", name="List", alias=None, is_relative=False, level=0)

        assert imp1 == imp2
        assert imp1 != imp3


class TestParameterKind:
    """Tests for ParameterKind enum."""

    def test_all_kinds_exist(self) -> None:
        """All Python parameter kinds represented."""
        assert ParameterKind.POSITIONAL_ONLY.value == "POSITIONAL_ONLY"
        assert ParameterKind.POSITIONAL_OR_KEYWORD.value == "POSITIONAL_OR_KEYWORD"
        assert ParameterKind.VAR_POSITIONAL.value == "VAR_POSITIONAL"
        assert ParameterKind.KEYWORD_ONLY.value == "KEYWORD_ONLY"
        assert ParameterKind.VAR_KEYWORD.value == "VAR_KEYWORD"

    def test_exhaustive_iteration(self) -> None:
        """Enum is iterable and has exactly 5 members."""
        kinds = list(ParameterKind)
        assert len(kinds) == 5


class TestParameter:
    """Tests for Parameter."""

    def test_positional_or_keyword(self) -> None:
        """Standard parameter: def f(x: int = 0)."""
        param = Parameter(
            name="x",
            annotation="int",
            default="0",
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )

        assert param.name == "x"
        assert param.annotation == "int"
        assert param.default == "0"
        assert param.kind == ParameterKind.POSITIONAL_OR_KEYWORD

    def test_positional_only(self) -> None:
        """Positional-only: def f(x, /)."""
        param = Parameter(
            name="x",
            annotation=None,
            default=None,
            kind=ParameterKind.POSITIONAL_ONLY,
        )

        assert param.kind == ParameterKind.POSITIONAL_ONLY

    def test_var_positional(self) -> None:
        """Var positional: def f(*args)."""
        param = Parameter(
            name="args",
            annotation=None,
            default=None,
            kind=ParameterKind.VAR_POSITIONAL,
        )

        assert param.name == "args"  # no asterisk in name
        assert param.kind == ParameterKind.VAR_POSITIONAL

    def test_keyword_only(self) -> None:
        """Keyword-only: def f(*, x)."""
        param = Parameter(
            name="x",
            annotation=None,
            default=None,
            kind=ParameterKind.KEYWORD_ONLY,
        )

        assert param.kind == ParameterKind.KEYWORD_ONLY

    def test_var_keyword(self) -> None:
        """Var keyword: def f(**kwargs)."""
        param = Parameter(
            name="kwargs",
            annotation=None,
            default=None,
            kind=ParameterKind.VAR_KEYWORD,
        )

        assert param.name == "kwargs"  # no asterisks in name
        assert param.kind == ParameterKind.VAR_KEYWORD

    def test_with_complex_annotation(self) -> None:
        """Parameter with union type annotation."""
        param = Parameter(
            name="value",
            annotation="str | int | None",
            default="None",
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )

        assert param.annotation == "str | int | None"

    def test_frozen_immutable(self) -> None:
        """Parameter is frozen (immutable)."""
        param = Parameter(
            name="x",
            annotation=None,
            default=None,
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )

        with pytest.raises(AttributeError):
            param.name = "y"  # type: ignore[misc]

    def test_hashable(self) -> None:
        """Parameter is hashable."""
        param = Parameter(
            name="x",
            annotation="int",
            default=None,
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )

        param_set = frozenset({param})
        assert param in param_set

    def test_equality(self) -> None:
        """Parameter equality based on all fields."""
        param1 = Parameter(
            name="x",
            annotation="int",
            default=None,
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )
        param2 = Parameter(
            name="x",
            annotation="int",
            default=None,
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )
        param3 = Parameter(
            name="y",
            annotation="int",
            default=None,
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )

        assert param1 == param2
        assert param1 != param3


class TestFunction:
    """Tests for Function."""

    def test_simple_function(self) -> None:
        """Simple function: def foo(): pass."""
        loc = Location(file="app/service.py", line=10, func="foo")
        func = Function(
            name="foo",
            qualified_name="app.service.foo",
            parameters=(),
            return_annotation=None,
            location=loc,
            is_async=False,
            is_generator=False,
            is_method=False,
            decorators=(),
            body_calls=(),
        )

        assert func.name == "foo"
        assert func.qualified_name == "app.service.foo"
        assert func.parameters == ()
        assert func.location == loc
        assert func.is_async is False
        assert func.is_method is False

    def test_async_function(self) -> None:
        """Async function: async def fetch(): ..."""
        loc = Location(file="app/api.py", line=20, func="fetch")
        func = Function(
            name="fetch",
            qualified_name="app.api.fetch",
            parameters=(),
            return_annotation="Response",
            location=loc,
            is_async=True,
            is_generator=False,
            is_method=False,
            decorators=(),
            body_calls=("client.get", "parse_response"),
        )

        assert func.is_async is True
        assert func.return_annotation == "Response"
        assert func.body_calls == ("client.get", "parse_response")

    def test_generator_function(self) -> None:
        """Generator function: def items(): yield x."""
        loc = Location(file="app/iter.py", line=5, func="items")
        func = Function(
            name="items",
            qualified_name="app.iter.items",
            parameters=(),
            return_annotation=None,
            location=loc,
            is_async=False,
            is_generator=True,
            is_method=False,
            decorators=(),
            body_calls=(),
        )

        assert func.is_generator is True

    def test_method(self) -> None:
        """Method: def process(self): ..."""
        loc = Location(file="app/service.py", line=15, func="process")
        self_param = Parameter(
            name="self",
            annotation=None,
            default=None,
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )
        func = Function(
            name="process",
            qualified_name="app.service.Service.process",
            parameters=(self_param,),
            return_annotation=None,
            location=loc,
            is_async=False,
            is_generator=False,
            is_method=True,
            decorators=(),
            body_calls=(),
        )

        assert func.is_method is True
        assert len(func.parameters) == 1

    def test_with_decorators(self) -> None:
        """Function with decorators."""
        loc = Location(file="app/api.py", line=30, func="handler")
        func = Function(
            name="handler",
            qualified_name="app.api.handler",
            parameters=(),
            return_annotation=None,
            location=loc,
            is_async=False,
            is_generator=False,
            is_method=False,
            decorators=("route", "authenticate"),
            body_calls=(),
        )

        assert func.decorators == ("route", "authenticate")

    def test_with_parameters(self) -> None:
        """Function with multiple parameters."""
        loc = Location(file="app/math.py", line=5, func="add")
        param_a = Parameter(
            name="a",
            annotation="int",
            default=None,
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )
        param_b = Parameter(
            name="b",
            annotation="int",
            default="0",
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
        )
        func = Function(
            name="add",
            qualified_name="app.math.add",
            parameters=(param_a, param_b),
            return_annotation="int",
            location=loc,
            is_async=False,
            is_generator=False,
            is_method=False,
            decorators=(),
            body_calls=(),
        )

        assert len(func.parameters) == 2
        assert func.parameters[0].name == "a"
        assert func.parameters[1].default == "0"

    def test_frozen_immutable(self) -> None:
        """Function is frozen (immutable)."""
        loc = Location(file="test.py", line=1, func="f")
        func = Function(
            name="f",
            qualified_name="test.f",
            parameters=(),
            return_annotation=None,
            location=loc,
            is_async=False,
            is_generator=False,
            is_method=False,
            decorators=(),
            body_calls=(),
        )

        with pytest.raises(AttributeError):
            func.name = "g"  # type: ignore[misc]

    def test_hashable(self) -> None:
        """Function is hashable."""
        loc = Location(file="test.py", line=1, func="f")
        func = Function(
            name="f",
            qualified_name="test.f",
            parameters=(),
            return_annotation=None,
            location=loc,
            is_async=False,
            is_generator=False,
            is_method=False,
            decorators=(),
            body_calls=(),
        )

        func_set = frozenset({func})
        assert func in func_set


class TestClass:
    """Tests for Class."""

    def test_simple_class(self) -> None:
        """Simple class: class Foo: pass."""
        loc = Location(file="app/models.py", line=5, func=None)
        cls = Class(
            name="Foo",
            qualified_name="app.models.Foo",
            bases=(),
            methods=(),
            location=loc,
            is_protocol=False,
            is_dataclass=False,
        )

        assert cls.name == "Foo"
        assert cls.qualified_name == "app.models.Foo"
        assert cls.bases == ()
        assert cls.methods == ()
        assert cls.is_protocol is False
        assert cls.is_dataclass is False

    def test_class_with_bases(self) -> None:
        """Class with inheritance: class User(BaseModel, Mixin)."""
        loc = Location(file="app/models.py", line=10, func=None)
        cls = Class(
            name="User",
            qualified_name="app.models.User",
            bases=("BaseModel", "Mixin"),
            methods=(),
            location=loc,
            is_protocol=False,
            is_dataclass=False,
        )

        assert cls.bases == ("BaseModel", "Mixin")

    def test_class_with_methods(self) -> None:
        """Class with methods."""
        loc = Location(file="app/service.py", line=1, func=None)
        method_loc = Location(file="app/service.py", line=3, func="process")
        method = Function(
            name="process",
            qualified_name="app.service.Service.process",
            parameters=(),
            return_annotation=None,
            location=method_loc,
            is_async=False,
            is_generator=False,
            is_method=True,
            decorators=(),
            body_calls=(),
        )
        cls = Class(
            name="Service",
            qualified_name="app.service.Service",
            bases=(),
            methods=(method,),
            location=loc,
            is_protocol=False,
            is_dataclass=False,
        )

        assert len(cls.methods) == 1
        assert cls.methods[0].name == "process"

    def test_protocol_class(self) -> None:
        """Protocol class."""
        loc = Location(file="app/ports.py", line=5, func=None)
        cls = Class(
            name="Repository",
            qualified_name="app.ports.Repository",
            bases=("Protocol",),
            methods=(),
            location=loc,
            is_protocol=True,
            is_dataclass=False,
        )

        assert cls.is_protocol is True

    def test_dataclass(self) -> None:
        """Dataclass."""
        loc = Location(file="app/dto.py", line=5, func=None)
        cls = Class(
            name="UserDTO",
            qualified_name="app.dto.UserDTO",
            bases=(),
            methods=(),
            location=loc,
            is_protocol=False,
            is_dataclass=True,
        )

        assert cls.is_dataclass is True

    def test_frozen_immutable(self) -> None:
        """Class is frozen (immutable)."""
        loc = Location(file="test.py", line=1, func=None)
        cls = Class(
            name="Foo",
            qualified_name="test.Foo",
            bases=(),
            methods=(),
            location=loc,
            is_protocol=False,
            is_dataclass=False,
        )

        with pytest.raises(AttributeError):
            cls.name = "Bar"  # type: ignore[misc]

    def test_hashable(self) -> None:
        """Class is hashable."""
        loc = Location(file="test.py", line=1, func=None)
        cls = Class(
            name="Foo",
            qualified_name="test.Foo",
            bases=(),
            methods=(),
            location=loc,
            is_protocol=False,
            is_dataclass=False,
        )

        cls_set = frozenset({cls})
        assert cls in cls_set


class TestModule:
    """Tests for Module."""

    def test_simple_module(self) -> None:
        """Simple module with minimal content."""
        mod = Module(
            name="app.utils",
            path=Path("src/app/utils.py"),
            imports=(),
            classes=(),
            functions=(),
            docstring=None,
        )

        assert mod.name == "app.utils"
        assert mod.path == Path("src/app/utils.py")
        assert mod.imports == ()
        assert mod.docstring is None

    def test_module_with_imports(self) -> None:
        """Module with imports."""
        imp = Import(module="typing", name="Optional", alias=None, is_relative=False, level=0)
        mod = Module(
            name="app.service",
            path=Path("src/app/service.py"),
            imports=(imp,),
            classes=(),
            functions=(),
            docstring=None,
        )

        assert len(mod.imports) == 1
        assert mod.imports[0].module == "typing"

    def test_module_with_functions(self) -> None:
        """Module with functions."""
        loc = Location(file="src/app/utils.py", line=5, func="helper")
        func = Function(
            name="helper",
            qualified_name="app.utils.helper",
            parameters=(),
            return_annotation=None,
            location=loc,
            is_async=False,
            is_generator=False,
            is_method=False,
            decorators=(),
            body_calls=(),
        )
        mod = Module(
            name="app.utils",
            path=Path("src/app/utils.py"),
            imports=(),
            classes=(),
            functions=(func,),
            docstring=None,
        )

        assert len(mod.functions) == 1

    def test_module_with_classes(self) -> None:
        """Module with classes."""
        loc = Location(file="src/app/models.py", line=10, func=None)
        cls = Class(
            name="User",
            qualified_name="app.models.User",
            bases=(),
            methods=(),
            location=loc,
            is_protocol=False,
            is_dataclass=False,
        )
        mod = Module(
            name="app.models",
            path=Path("src/app/models.py"),
            imports=(),
            classes=(cls,),
            functions=(),
            docstring=None,
        )

        assert len(mod.classes) == 1

    def test_module_with_docstring(self) -> None:
        """Module with docstring."""
        mod = Module(
            name="app",
            path=Path("src/app/__init__.py"),
            imports=(),
            classes=(),
            functions=(),
            docstring="Application package.",
        )

        assert mod.docstring == "Application package."

    def test_frozen_immutable(self) -> None:
        """Module is frozen (immutable)."""
        mod = Module(
            name="test",
            path=Path("test.py"),
            imports=(),
            classes=(),
            functions=(),
            docstring=None,
        )

        with pytest.raises(AttributeError):
            mod.name = "other"  # type: ignore[misc]


class TestCodebase:
    """Tests for Codebase."""

    def test_empty_codebase(self) -> None:
        """Empty codebase via classmethod."""
        codebase = Codebase.empty()

        assert codebase.root_path == Path()
        assert codebase.root_package == ""
        assert len(codebase.modules) == 0

    def test_codebase_with_modules(self) -> None:
        """Codebase with modules."""
        mod = Module(
            name="app.utils",
            path=Path("src/app/utils.py"),
            imports=(),
            classes=(),
            functions=(),
            docstring=None,
        )
        codebase = Codebase(
            root_path=Path("src"),
            root_package="app",
            modules={"app.utils": mod},
        )

        assert codebase.root_path == Path("src")
        assert codebase.root_package == "app"
        assert "app.utils" in codebase.modules
        assert codebase.modules["app.utils"] == mod

    def test_module_name_key_mismatch_raises(self) -> None:
        """Module.name != key raises ValueError (FAIL-FIRST)."""
        mod = Module(
            name="app.utils",
            path=Path("src/app/utils.py"),
            imports=(),
            classes=(),
            functions=(),
            docstring=None,
        )

        with pytest.raises(ValueError, match=r"module name .* does not match key"):
            Codebase(
                root_path=Path("src"),
                root_package="app",
                modules={"wrong.key": mod},  # key != mod.name
            )

    def test_frozen_immutable(self) -> None:
        """Codebase is frozen (immutable)."""
        codebase = Codebase.empty()

        with pytest.raises(AttributeError):
            codebase.root_path = Path("/other")  # type: ignore[misc]

    def test_multiple_modules(self) -> None:
        """Codebase with multiple modules."""
        mod1 = Module(
            name="app.models",
            path=Path("src/app/models.py"),
            imports=(),
            classes=(),
            functions=(),
            docstring=None,
        )
        mod2 = Module(
            name="app.service",
            path=Path("src/app/service.py"),
            imports=(),
            classes=(),
            functions=(),
            docstring=None,
        )
        codebase = Codebase(
            root_path=Path("src"),
            root_package="app",
            modules={"app.models": mod1, "app.service": mod2},
        )

        assert len(codebase.modules) == 2
        assert "app.models" in codebase.modules
        assert "app.service" in codebase.modules
