"""Tests for call_resolver.

Tests:
- Symbol table construction
- Import resolution (absolute, relative)
- Name resolution (direct, constructor)
- Method resolution (self.method)
- Super resolution (super().method)
- Attribute resolution (module.func)
- Unresolved tracking (builtin, external, dynamic, undefined)
"""

from pathlib import Path

from archcheck.domain.codebase import (
    Class,
    Codebase,
    Function,
    Import,
    Module,
)
from archcheck.domain.events import Location
from archcheck.domain.static_graph import CallType
from archcheck.infrastructure.analyzers.call_resolver import resolve_calls


def _make_location(line: int = 1) -> Location:
    """Create test location."""
    return Location(file=None, line=line, func=None)


def _make_function(
    name: str,
    module_name: str,
    *,
    class_name: str | None = None,
    body_calls: tuple[str, ...] = (),
    decorators: tuple[str, ...] = (),
) -> Function:
    """Create test function."""
    qualified_name = f"{module_name}.{class_name}.{name}" if class_name else f"{module_name}.{name}"

    return Function(
        name=name,
        qualified_name=qualified_name,
        parameters=(),
        return_annotation=None,
        location=_make_location(),
        is_async=False,
        is_generator=False,
        is_method=class_name is not None,
        decorators=decorators,
        body_calls=body_calls,
    )


def _make_class(
    name: str,
    module_name: str,
    *,
    methods: tuple[Function, ...] = (),
    bases: tuple[str, ...] = (),
) -> Class:
    """Create test class."""
    return Class(
        name=name,
        qualified_name=f"{module_name}.{name}",
        bases=bases,
        methods=methods,
        location=_make_location(),
        is_protocol=False,
        is_dataclass=False,
    )


def _make_module(
    name: str,
    *,
    imports: tuple[Import, ...] = (),
    functions: tuple[Function, ...] = (),
    classes: tuple[Class, ...] = (),
) -> Module:
    """Create test module."""
    return Module(
        name=name,
        path=Path(f"{name.replace('.', '/')}.py"),
        imports=imports,
        classes=classes,
        functions=functions,
        docstring=None,
    )


class TestSymbolTable:
    """Tests for symbol table construction."""

    def test_import_absolute(self) -> None:
        """Import typing adds 'typing' to symbol table."""
        module = _make_module(
            "app.main",
            imports=(Import("typing", None, None, is_relative=False, level=0),),
            functions=(_make_function("foo", "app.main", body_calls=("typing",)),),
        )
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        # typing is external, should be unresolved
        assert len(unresolved) == 1
        assert unresolved[0].callee_name == "typing"
        assert unresolved[0].reason == "external"

    def test_from_import(self) -> None:
        """From X import Y adds 'Y' to symbol table."""
        module = _make_module(
            "app.main",
            imports=(Import("typing", "Optional", None, is_relative=False, level=0),),
            functions=(_make_function("foo", "app.main", body_calls=("Optional",)),),
        )
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        assert len(unresolved) == 1
        assert unresolved[0].callee_name == "Optional"
        assert unresolved[0].reason == "external"

    def test_import_as(self) -> None:
        """Import X as Y adds 'Y' to symbol table."""
        module = _make_module(
            "app.main",
            imports=(Import("typing", None, "t", is_relative=False, level=0),),
            functions=(_make_function("foo", "app.main", body_calls=("t",)),),
        )
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        assert len(unresolved) == 1
        assert unresolved[0].callee_name == "t"

    def test_own_function_in_symbol_table(self) -> None:
        """Module's own functions are in symbol table."""
        helper = _make_function("helper", "app.main")
        caller = _make_function("caller", "app.main", body_calls=("helper",))
        module = _make_module("app.main", functions=(helper, caller))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        edges, _unresolved = resolve_calls(module, codebase)

        assert len(edges) == 1
        assert edges[0].caller_fqn == "app.main.caller"
        assert edges[0].callee_fqn == "app.main.helper"
        assert edges[0].call_type == CallType.DIRECT

    def test_own_class_in_symbol_table(self) -> None:
        """Module's own classes are in symbol table as CONSTRUCTOR."""
        cls = _make_class("Service", "app.main")
        caller = _make_function("caller", "app.main", body_calls=("Service",))
        module = _make_module("app.main", functions=(caller,), classes=(cls,))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        edges, _unresolved = resolve_calls(module, codebase)

        assert len(edges) == 1
        assert edges[0].callee_fqn == "app.main.Service"
        assert edges[0].call_type == CallType.CONSTRUCTOR


class TestRelativeImport:
    """Tests for relative import resolution."""

    def test_level_1_import_function(self) -> None:
        """From . import func → resolves to parent.func."""
        # from .utils import helper
        imp = Import("utils", "helper", None, is_relative=True, level=1)
        helper_func = _make_function("helper", "app.services.utils")
        utils_module = _make_module("app.services.utils", functions=(helper_func,))
        module = _make_module(
            "app.services.user",
            imports=(imp,),
            functions=(_make_function("foo", "app.services.user", body_calls=("helper",)),),
        )
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={
                "app.services.user": module,
                "app.services.utils": utils_module,
            },
        )

        edges, _unresolved = resolve_calls(module, codebase)

        assert len(edges) == 1
        assert edges[0].callee_fqn == "app.services.utils.helper"

    def test_level_2_parent_package(self) -> None:
        """From ..models import User → parent.parent.models.User."""
        imp = Import("models", "User", None, is_relative=True, level=2)
        user_cls = _make_class("User", "app.models")
        models_module = _make_module("app.models", classes=(user_cls,))
        module = _make_module(
            "app.services.user",
            imports=(imp,),
            functions=(_make_function("foo", "app.services.user", body_calls=("User",)),),
        )
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={
                "app.services.user": module,
                "app.models": models_module,
            },
        )

        edges, _unresolved = resolve_calls(module, codebase)

        assert len(edges) == 1
        assert edges[0].callee_fqn == "app.models.User"
        assert edges[0].call_type == CallType.CONSTRUCTOR


class TestMethodResolution:
    """Tests for self.method() resolution."""

    def test_self_method_found(self) -> None:
        """Self.method() resolves to class method."""
        process = _make_function("process", "app.main", class_name="Service")
        helper = _make_function(
            "helper",
            "app.main",
            class_name="Service",
            body_calls=("self.process",),
        )
        cls = _make_class("Service", "app.main", methods=(process, helper))
        module = _make_module("app.main", classes=(cls,))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        edges, _unresolved = resolve_calls(module, codebase)

        assert len(edges) == 1
        assert edges[0].caller_fqn == "app.main.Service.helper"
        assert edges[0].callee_fqn == "app.main.Service.process"
        assert edges[0].call_type == CallType.METHOD

    def test_self_method_not_found(self) -> None:
        """Self.method() with missing method → unresolved."""
        helper = _make_function(
            "helper",
            "app.main",
            class_name="Service",
            body_calls=("self.missing",),
        )
        cls = _make_class("Service", "app.main", methods=(helper,))
        module = _make_module("app.main", classes=(cls,))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        assert len(unresolved) == 1
        assert unresolved[0].callee_name == "self.missing"
        assert unresolved[0].reason == "method not found"

    def test_self_outside_class(self) -> None:
        """Self.method() in top-level function → unresolved."""
        func = _make_function("foo", "app.main", body_calls=("self.bar",))
        module = _make_module("app.main", functions=(func,))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        assert len(unresolved) == 1
        assert unresolved[0].reason == "self outside class"


class TestSuperResolution:
    """Tests for super().method() resolution."""

    def test_super_method_found(self) -> None:
        """Super().method() resolves to parent method."""
        parent_method = _make_function("process", "app.main", class_name="Base")
        parent_cls = _make_class("Base", "app.main", methods=(parent_method,))

        child_method = _make_function(
            "process",
            "app.main",
            class_name="Child",
            body_calls=("super().process",),
        )
        child_cls = _make_class(
            "Child",
            "app.main",
            methods=(child_method,),
            bases=("Base",),
        )

        module = _make_module("app.main", classes=(parent_cls, child_cls))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        edges, _unresolved = resolve_calls(module, codebase)

        assert len(edges) == 1
        assert edges[0].callee_fqn == "app.main.Base.process"
        assert edges[0].call_type == CallType.SUPER

    def test_super_method_not_found(self) -> None:
        """Super().method() with missing parent method → unresolved."""
        child_method = _make_function(
            "process",
            "app.main",
            class_name="Child",
            body_calls=("super().missing",),
        )
        child_cls = _make_class(
            "Child",
            "app.main",
            methods=(child_method,),
            bases=("Base",),
        )
        module = _make_module("app.main", classes=(child_cls,))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        assert len(unresolved) == 1
        assert unresolved[0].reason == "parent method not found"


class TestAttributeResolution:
    """Tests for module.func() resolution."""

    def test_module_function_call(self) -> None:
        """Module.func() resolves when module imported with alias."""
        utils_func = _make_function("helper", "app.utils")
        utils_module = _make_module("app.utils", functions=(utils_func,))

        # import app.utils as utils → symbol_table["utils"] = "app.utils"
        imp = Import("app.utils", None, "utils", is_relative=False, level=0)
        caller = _make_function("foo", "app.main", body_calls=("utils.helper",))
        module = _make_module("app.main", imports=(imp,), functions=(caller,))

        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={
                "app.main": module,
                "app.utils": utils_module,
            },
        )

        edges, _unresolved = resolve_calls(module, codebase)

        assert len(edges) == 1
        assert edges[0].callee_fqn == "app.utils.helper"
        assert edges[0].call_type == CallType.DIRECT

    def test_dynamic_attribute_call(self) -> None:
        """Obj.method() without type info → dynamic."""
        func = _make_function("foo", "app.main", body_calls=("obj.method",))
        module = _make_module("app.main", functions=(func,))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        assert len(unresolved) == 1
        assert unresolved[0].callee_name == "obj.method"
        assert unresolved[0].reason == "dynamic"


class TestDecoratorResolution:
    """Tests for decorator resolution."""

    def test_decorator_resolved(self) -> None:
        """Decorator resolves to DECORATOR call type."""
        decorator = _make_function("route", "app.main")
        decorated = _make_function("handler", "app.main", decorators=("route",))
        module = _make_module("app.main", functions=(decorator, decorated))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        edges, _unresolved = resolve_calls(module, codebase)

        assert len(edges) == 1
        assert edges[0].callee_fqn == "app.main.route"
        assert edges[0].call_type == CallType.DECORATOR

    def test_decorator_with_args(self) -> None:
        """Decorator with args extracts base name."""
        decorator = _make_function("route", "app.main")
        decorated = _make_function("handler", "app.main", decorators=("route('/api')",))
        module = _make_module("app.main", functions=(decorator, decorated))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        edges, _unresolved = resolve_calls(module, codebase)

        assert len(edges) == 1
        assert edges[0].callee_fqn == "app.main.route"


class TestUnresolvedReasons:
    """Tests for unresolved call reasons."""

    def test_builtin(self) -> None:
        """Builtin function → reason='builtin'."""
        func = _make_function("foo", "app.main", body_calls=("print",))
        module = _make_module("app.main", functions=(func,))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        assert len(unresolved) == 1
        assert unresolved[0].callee_name == "print"
        assert unresolved[0].reason == "builtin"

    def test_undefined(self) -> None:
        """Unknown name → reason='undefined'."""
        func = _make_function("foo", "app.main", body_calls=("unknown_func",))
        module = _make_module("app.main", functions=(func,))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        assert len(unresolved) == 1
        assert unresolved[0].callee_name == "unknown_func"
        assert unresolved[0].reason == "undefined"

    def test_external(self) -> None:
        """Imported but not in codebase → reason='external'."""
        imp = Import("requests", "get", None, is_relative=False, level=0)
        func = _make_function("foo", "app.main", body_calls=("get",))
        module = _make_module("app.main", imports=(imp,), functions=(func,))
        codebase = Codebase(
            root_path=Path(),
            root_package="app",
            modules={"app.main": module},
        )

        _edges, unresolved = resolve_calls(module, codebase)

        assert len(unresolved) == 1
        assert unresolved[0].callee_name == "get"
        assert unresolved[0].reason == "external"
