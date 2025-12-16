"""Fluent API (DSL) for architecture testing.

Entry point for fluent architecture queries and assertions.

Example:
    arch = ArchCheck(codebase)
    arch.modules().in_layer("domain").should().not_import("infrastructure.**").assert_check()
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from archcheck.domain.exceptions.base import ArchCheckError
from archcheck.domain.exceptions.violation import ArchitectureViolationError
from archcheck.domain.model.edge_nature import EdgeNature
from archcheck.presentation.api._checks import (
    make_class_extends_check,
    make_class_implements_check,
    make_class_in_layer_check,
    make_class_max_methods_check,
    make_edge_be_allowed_check,
    make_edge_not_cross_boundary_check,
    make_function_in_layer_check,
    make_function_no_call_check,
    make_function_only_call_check,
    make_in_layer_check,
    make_no_import_check,
    make_only_import_check,
)
from archcheck.presentation.api._helpers import execute_checks, execute_query, get_layer
from archcheck.presentation.api.patterns import compile_pattern

if TYPE_CHECKING:
    from archcheck.domain.model.class_ import Class
    from archcheck.domain.model.codebase import Codebase
    from archcheck.domain.model.function import Function
    from archcheck.domain.model.function_edge import FunctionEdge
    from archcheck.domain.model.merged_call_graph import MergedCallGraph
    from archcheck.domain.model.module import Module
    from archcheck.domain.model.violation import Violation


class ArchCheck:
    """Entry point for architecture analysis.

    Provides fluent API for querying and asserting architecture rules.

    Attributes:
        _codebase: Parsed codebase
        _graph: Optional merged call graph (required for edges())
    """

    def __init__(
        self,
        codebase: Codebase,
        graph: MergedCallGraph | None = None,
    ) -> None:
        """Initialize architecture checker.

        Args:
            codebase: Parsed codebase to analyze
            graph: Optional merged call graph for edge queries

        Raises:
            TypeError: If codebase is None
        """
        if codebase is None:
            raise TypeError("codebase must not be None")
        self._codebase = codebase
        self._graph = graph

    def modules(self) -> ModuleQuery:
        """Start module query.

        Returns:
            ModuleQuery for chaining filters
        """
        return ModuleQuery.create(self._codebase)

    def classes(self) -> ClassQuery:
        """Start class query.

        Returns:
            ClassQuery for chaining filters
        """
        return ClassQuery.create(self._codebase)

    def functions(self) -> FunctionQuery:
        """Start function query.

        Returns:
            FunctionQuery for chaining filters
        """
        return FunctionQuery.create(self._codebase)

    def edges(self) -> EdgeQuery:
        """Start edge query.

        Requires MergedCallGraph (use arch_with_graph fixture).

        Returns:
            EdgeQuery for chaining filters

        Raises:
            ArchCheckError: If graph was not provided
        """
        return EdgeQuery.create(self.graph)

    @property
    def codebase(self) -> Codebase:
        """Access underlying codebase."""
        return self._codebase

    @property
    def graph(self) -> MergedCallGraph:
        """Access merged call graph.

        Raises:
            ArchCheckError: If graph was not provided
        """
        if self._graph is None:
            raise ArchCheckError(
                "MergedCallGraph not available. "
                "Use ArchCheck(codebase, graph) or arch_with_graph fixture."
            )
        return self._graph


@dataclass(frozen=True, slots=True)
class ModuleQuery:
    """Immutable query builder for modules.

    Supports chaining filters before transitioning to assertions.
    """

    _codebase: Codebase
    _filters: tuple[Callable[[Module], bool], ...] = ()

    @classmethod
    def create(cls, codebase: Codebase) -> ModuleQuery:
        """Create new query for codebase.

        Args:
            codebase: Codebase to query

        Returns:
            Fresh ModuleQuery with no filters
        """
        return cls(_codebase=codebase)

    def _with_filter(self, predicate: Callable[[Module], bool]) -> ModuleQuery:
        """Return new query with additional filter.

        Args:
            predicate: Filter predicate

        Returns:
            New ModuleQuery with added filter (immutable)
        """
        return ModuleQuery(
            _codebase=self._codebase,
            _filters=(*self._filters, predicate),
        )

    def in_layer(self, layer: str) -> ModuleQuery:
        """Filter modules in specific layer.

        Layer is first segment after root package.
        Example: myapp.domain.user has layer "domain".

        Args:
            layer: Layer name to filter

        Returns:
            Filtered ModuleQuery
        """
        return self._with_filter(lambda m: get_layer(m.name) == layer)

    def in_package(self, prefix: str) -> ModuleQuery:
        """Filter modules by package prefix.

        Matches modules starting with prefix (with dot boundary).
        Example: in_package("myapp.domain") matches myapp.domain.user

        Args:
            prefix: Package prefix

        Returns:
            Filtered ModuleQuery
        """
        # Match exact prefix or prefix + dot
        return self._with_filter(lambda m: m.name == prefix or m.name.startswith(prefix + "."))

    def matching(self, pattern: str) -> ModuleQuery:
        """Filter modules by name pattern.

        Supports glob patterns: *, **, ?
        See patterns.py for syntax.

        Args:
            pattern: Glob pattern

        Returns:
            Filtered ModuleQuery
        """
        compiled = compile_pattern(pattern)
        return self._with_filter(lambda m: compiled.match(m.name))

    def that(self, predicate: Callable[[Module], bool]) -> ModuleQuery:
        """Filter by custom predicate.

        Args:
            predicate: Function returning True for matching modules

        Returns:
            Filtered ModuleQuery
        """
        return self._with_filter(predicate)

    def should(self) -> ModuleAssertion:
        """Transition to assertion mode.

        Executes filters and returns assertion builder.

        Returns:
            ModuleAssertion with filtered modules
        """
        modules = execute_query(self._codebase.modules.values(), self._filters)
        return ModuleAssertion(_modules=modules)

    def execute(self) -> tuple[Module, ...]:
        """Execute query and return matching modules.

        Returns:
            Tuple of modules matching all filters
        """
        return execute_query(self._codebase.modules.values(), self._filters)


@dataclass(frozen=True, slots=True)
class ModuleAssertion:
    """Immutable assertion builder for modules.

    Supports chaining assertions before execution.
    """

    _modules: tuple[Module, ...]
    _checks: tuple[Callable[[Module], Violation | None], ...] = ()

    def _with_check(
        self,
        check: Callable[[Module], Violation | None],
    ) -> ModuleAssertion:
        """Return new assertion with additional check.

        Args:
            check: Check function

        Returns:
            New ModuleAssertion with added check (immutable)
        """
        return ModuleAssertion(
            _modules=self._modules,
            _checks=(*self._checks, check),
        )

    def not_import(self, *patterns: str) -> ModuleAssertion:
        """Assert modules don't import patterns.

        Args:
            *patterns: Forbidden import patterns (at least one required)

        Returns:
            Assertion with added check

        Raises:
            ValueError: If no patterns provided
        """
        if not patterns:
            raise ValueError("at least one pattern required")
        compiled = tuple(compile_pattern(p) for p in patterns)
        return self._with_check(make_no_import_check(compiled))

    def only_import(self, *patterns: str) -> ModuleAssertion:
        """Assert modules only import from patterns.

        Args:
            *patterns: Allowed import patterns (at least one required)

        Returns:
            Assertion with added check

        Raises:
            ValueError: If no patterns provided
        """
        if not patterns:
            raise ValueError("at least one pattern required")
        compiled = tuple(compile_pattern(p) for p in patterns)
        return self._with_check(make_only_import_check(compiled))

    def be_in_layer(self, layer: str) -> ModuleAssertion:
        """Assert modules are in specific layer.

        Args:
            layer: Expected layer name

        Returns:
            Assertion with added check
        """
        return self._with_check(make_in_layer_check(layer))

    def collect(self) -> tuple[Violation, ...]:
        """Execute checks and return violations.

        Returns:
            Tuple of all violations found
        """
        return execute_checks(self._modules, self._checks)

    def assert_check(self) -> None:
        """Execute checks and raise on violations.

        Raises:
            ArchitectureViolationError: If any violations found
        """
        violations = self.collect()
        if violations:
            raise ArchitectureViolationError(violations)

    def is_valid(self) -> bool:
        """Check if all assertions pass.

        Returns:
            True if no violations, False otherwise
        """
        return len(self.collect()) == 0

    @property
    def module_count(self) -> int:
        """Number of modules being checked."""
        return len(self._modules)


@dataclass(frozen=True, slots=True)
class ClassQuery:
    """Immutable query builder for classes.

    Supports chaining filters before transitioning to assertions.
    """

    _codebase: Codebase
    _filters: tuple[Callable[[Class], bool], ...] = ()

    @classmethod
    def create(cls, codebase: Codebase) -> ClassQuery:
        """Create new query for codebase.

        Args:
            codebase: Codebase to query

        Returns:
            Fresh ClassQuery with no filters
        """
        return cls(_codebase=codebase)

    def _with_filter(self, predicate: Callable[[Class], bool]) -> ClassQuery:
        """Return new query with additional filter.

        Args:
            predicate: Filter predicate

        Returns:
            New ClassQuery with added filter (immutable)
        """
        return ClassQuery(
            _codebase=self._codebase,
            _filters=(*self._filters, predicate),
        )

    def in_layer(self, layer: str) -> ClassQuery:
        """Filter classes in specific layer.

        Layer is first segment after root package.
        Example: myapp.domain.User has layer "domain".

        Args:
            layer: Layer name to filter

        Returns:
            Filtered ClassQuery
        """
        return self._with_filter(lambda c: get_layer(c.qualified_name) == layer)

    def in_package(self, prefix: str) -> ClassQuery:
        """Filter classes by package prefix.

        Matches classes in modules starting with prefix.
        Example: in_package("myapp.domain") matches myapp.domain.user.User

        Args:
            prefix: Package prefix

        Returns:
            Filtered ClassQuery
        """
        return self._with_filter(
            lambda c: (
                c.qualified_name.startswith(prefix + ".")
                or c.qualified_name.rsplit(".", 1)[0] == prefix
            )
        )

    def matching(self, pattern: str) -> ClassQuery:
        """Filter classes by qualified name pattern.

        Supports glob patterns: *, **, ?
        See patterns.py for syntax.

        Args:
            pattern: Glob pattern for qualified name

        Returns:
            Filtered ClassQuery
        """
        compiled = compile_pattern(pattern)
        return self._with_filter(lambda c: compiled.match(c.qualified_name))

    def named(self, pattern: str) -> ClassQuery:
        """Filter classes by class name pattern.

        Args:
            pattern: Glob pattern for class name (without module)

        Returns:
            Filtered ClassQuery
        """
        compiled = compile_pattern(pattern)
        return self._with_filter(lambda c: compiled.match(c.name))

    def extending(self, base: str) -> ClassQuery:
        """Filter classes extending base.

        Args:
            base: Base class pattern

        Returns:
            Filtered ClassQuery
        """
        compiled = compile_pattern(base)
        return self._with_filter(lambda c: any(compiled.match(b) for b in c.bases))

    def that(self, predicate: Callable[[Class], bool]) -> ClassQuery:
        """Filter by custom predicate.

        Args:
            predicate: Function returning True for matching classes

        Returns:
            Filtered ClassQuery
        """
        return self._with_filter(predicate)

    def should(self) -> ClassAssertion:
        """Transition to assertion mode.

        Executes filters and returns assertion builder.

        Returns:
            ClassAssertion with filtered classes
        """
        classes = execute_query(self._codebase.iter_classes(), self._filters)
        return ClassAssertion(_classes=classes)

    def execute(self) -> tuple[Class, ...]:
        """Execute query and return matching classes.

        Returns:
            Tuple of classes matching all filters
        """
        return execute_query(self._codebase.iter_classes(), self._filters)


@dataclass(frozen=True, slots=True)
class ClassAssertion:
    """Immutable assertion builder for classes.

    Supports chaining assertions before execution.
    """

    _classes: tuple[Class, ...]
    _checks: tuple[Callable[[Class], Violation | None], ...] = ()

    def _with_check(
        self,
        check: Callable[[Class], Violation | None],
    ) -> ClassAssertion:
        """Return new assertion with additional check.

        Args:
            check: Check function

        Returns:
            New ClassAssertion with added check (immutable)
        """
        return ClassAssertion(
            _classes=self._classes,
            _checks=(*self._checks, check),
        )

    def extend(self, base: str) -> ClassAssertion:
        """Assert classes extend base.

        Args:
            base: Base class pattern

        Returns:
            Assertion with added check
        """
        compiled = compile_pattern(base)
        return self._with_check(make_class_extends_check(compiled))

    def implement(self, protocol: str) -> ClassAssertion:
        """Assert classes implement protocol.

        Args:
            protocol: Protocol pattern

        Returns:
            Assertion with added check
        """
        compiled = compile_pattern(protocol)
        return self._with_check(make_class_implements_check(compiled))

    def be_in_layer(self, layer: str) -> ClassAssertion:
        """Assert classes are in specific layer.

        Args:
            layer: Expected layer name

        Returns:
            Assertion with added check
        """
        return self._with_check(make_class_in_layer_check(layer))

    def have_max_methods(self, n: int) -> ClassAssertion:
        """Assert classes have at most n public methods.

        Args:
            n: Maximum public methods

        Returns:
            Assertion with added check

        Raises:
            ValueError: If n < 1
        """
        if n < 1:
            raise ValueError("max methods must be >= 1")
        return self._with_check(make_class_max_methods_check(n))

    def collect(self) -> tuple[Violation, ...]:
        """Execute checks and return violations.

        Returns:
            Tuple of all violations found
        """
        return execute_checks(self._classes, self._checks)

    def assert_check(self) -> None:
        """Execute checks and raise on violations.

        Raises:
            ArchitectureViolationError: If any violations found
        """
        violations = self.collect()
        if violations:
            raise ArchitectureViolationError(violations)

    def is_valid(self) -> bool:
        """Check if all assertions pass.

        Returns:
            True if no violations, False otherwise
        """
        return len(self.collect()) == 0

    @property
    def class_count(self) -> int:
        """Number of classes being checked."""
        return len(self._classes)


@dataclass(frozen=True, slots=True)
class FunctionQuery:
    """Immutable query builder for functions.

    Supports chaining filters before transitioning to assertions.
    """

    _codebase: Codebase
    _filters: tuple[Callable[[Function], bool], ...] = ()

    @classmethod
    def create(cls, codebase: Codebase) -> FunctionQuery:
        """Create new query for codebase.

        Args:
            codebase: Codebase to query

        Returns:
            Fresh FunctionQuery with no filters
        """
        return cls(_codebase=codebase)

    def _with_filter(self, predicate: Callable[[Function], bool]) -> FunctionQuery:
        """Return new query with additional filter.

        Args:
            predicate: Filter predicate

        Returns:
            New FunctionQuery with added filter (immutable)
        """
        return FunctionQuery(
            _codebase=self._codebase,
            _filters=(*self._filters, predicate),
        )

    def in_layer(self, layer: str) -> FunctionQuery:
        """Filter functions in specific layer.

        Layer is first segment after root package.

        Args:
            layer: Layer name to filter

        Returns:
            Filtered FunctionQuery
        """
        return self._with_filter(lambda f: get_layer(f.qualified_name) == layer)

    def in_module(self, module: str) -> FunctionQuery:
        """Filter functions by module pattern.

        Args:
            module: Module pattern

        Returns:
            Filtered FunctionQuery
        """
        compiled = compile_pattern(module)
        return self._with_filter(lambda f: compiled.match(f.qualified_name.rsplit(".", 1)[0]))

    def matching(self, pattern: str) -> FunctionQuery:
        """Filter functions by qualified name pattern.

        Args:
            pattern: Glob pattern for qualified name

        Returns:
            Filtered FunctionQuery
        """
        compiled = compile_pattern(pattern)
        return self._with_filter(lambda f: compiled.match(f.qualified_name))

    def named(self, pattern: str) -> FunctionQuery:
        """Filter functions by function name pattern.

        Args:
            pattern: Glob pattern for function name

        Returns:
            Filtered FunctionQuery
        """
        compiled = compile_pattern(pattern)
        return self._with_filter(lambda f: compiled.match(f.name))

    def async_only(self) -> FunctionQuery:
        """Filter to only async functions.

        Returns:
            Filtered FunctionQuery
        """
        return self._with_filter(lambda f: f.is_async)

    def methods_only(self) -> FunctionQuery:
        """Filter to only methods (not module-level functions).

        Returns:
            Filtered FunctionQuery
        """
        return self._with_filter(lambda f: f.is_method)

    def module_level_only(self) -> FunctionQuery:
        """Filter to only module-level functions (not methods).

        Returns:
            Filtered FunctionQuery
        """
        return self._with_filter(lambda f: not f.is_method)

    def that(self, predicate: Callable[[Function], bool]) -> FunctionQuery:
        """Filter by custom predicate.

        Args:
            predicate: Function returning True for matching functions

        Returns:
            Filtered FunctionQuery
        """
        return self._with_filter(predicate)

    def should(self) -> FunctionAssertion:
        """Transition to assertion mode.

        Executes filters and returns assertion builder.

        Returns:
            FunctionAssertion with filtered functions
        """
        functions = execute_query(self._codebase.iter_functions(), self._filters)
        return FunctionAssertion(_functions=functions)

    def execute(self) -> tuple[Function, ...]:
        """Execute query and return matching functions.

        Returns:
            Tuple of functions matching all filters
        """
        return execute_query(self._codebase.iter_functions(), self._filters)


@dataclass(frozen=True, slots=True)
class FunctionAssertion:
    """Immutable assertion builder for functions.

    Supports chaining assertions before execution.
    """

    _functions: tuple[Function, ...]
    _checks: tuple[Callable[[Function], Violation | None], ...] = ()

    def _with_check(
        self,
        check: Callable[[Function], Violation | None],
    ) -> FunctionAssertion:
        """Return new assertion with additional check.

        Args:
            check: Check function

        Returns:
            New FunctionAssertion with added check (immutable)
        """
        return FunctionAssertion(
            _functions=self._functions,
            _checks=(*self._checks, check),
        )

    def not_call(self, *patterns: str) -> FunctionAssertion:
        """Assert functions don't call patterns.

        Args:
            *patterns: Forbidden call patterns (at least one required)

        Returns:
            Assertion with added check

        Raises:
            ValueError: If no patterns provided
        """
        if not patterns:
            raise ValueError("at least one pattern required")
        compiled = tuple(compile_pattern(p) for p in patterns)
        return self._with_check(make_function_no_call_check(compiled))

    def only_call(self, *patterns: str) -> FunctionAssertion:
        """Assert functions only call patterns.

        Args:
            *patterns: Allowed call patterns (at least one required)

        Returns:
            Assertion with added check

        Raises:
            ValueError: If no patterns provided
        """
        if not patterns:
            raise ValueError("at least one pattern required")
        compiled = tuple(compile_pattern(p) for p in patterns)
        return self._with_check(make_function_only_call_check(compiled))

    def be_in_layer(self, layer: str) -> FunctionAssertion:
        """Assert functions are in specific layer.

        Args:
            layer: Expected layer name

        Returns:
            Assertion with added check
        """
        return self._with_check(make_function_in_layer_check(layer))

    def collect(self) -> tuple[Violation, ...]:
        """Execute checks and return violations.

        Returns:
            Tuple of all violations found
        """
        return execute_checks(self._functions, self._checks)

    def assert_check(self) -> None:
        """Execute checks and raise on violations.

        Raises:
            ArchitectureViolationError: If any violations found
        """
        violations = self.collect()
        if violations:
            raise ArchitectureViolationError(violations)

    def is_valid(self) -> bool:
        """Check if all assertions pass.

        Returns:
            True if no violations, False otherwise
        """
        return len(self.collect()) == 0

    @property
    def function_count(self) -> int:
        """Number of functions being checked."""
        return len(self._functions)


@dataclass(frozen=True, slots=True)
class EdgeQuery:
    """Immutable query builder for edges.

    Supports chaining filters before transitioning to assertions.
    """

    _graph: MergedCallGraph
    _filters: tuple[Callable[[FunctionEdge], bool], ...] = ()

    @classmethod
    def create(cls, graph: MergedCallGraph) -> EdgeQuery:
        """Create new query for graph.

        Args:
            graph: MergedCallGraph to query

        Returns:
            Fresh EdgeQuery with no filters
        """
        return cls(_graph=graph)

    def _with_filter(self, predicate: Callable[[FunctionEdge], bool]) -> EdgeQuery:
        """Return new query with additional filter.

        Args:
            predicate: Filter predicate

        Returns:
            New EdgeQuery with added filter (immutable)
        """
        return EdgeQuery(
            _graph=self._graph,
            _filters=(*self._filters, predicate),
        )

    def from_layer(self, layer: str) -> EdgeQuery:
        """Filter edges where caller is in layer.

        Args:
            layer: Caller layer name

        Returns:
            Filtered EdgeQuery
        """
        return self._with_filter(lambda e: get_layer(e.caller_fqn) == layer)

    def to_layer(self, layer: str) -> EdgeQuery:
        """Filter edges where callee is in layer.

        Args:
            layer: Callee layer name

        Returns:
            Filtered EdgeQuery
        """
        return self._with_filter(lambda e: get_layer(e.callee_fqn) == layer)

    def crossing_boundary(self) -> EdgeQuery:
        """Filter edges that cross layer boundaries.

        Returns:
            Filtered EdgeQuery with only cross-layer edges
        """
        return self._with_filter(lambda e: get_layer(e.caller_fqn) != get_layer(e.callee_fqn))

    def with_nature(self, nature: EdgeNature) -> EdgeQuery:
        """Filter edges by nature.

        Args:
            nature: Required EdgeNature

        Returns:
            Filtered EdgeQuery
        """
        return self._with_filter(lambda e: e.nature == nature)

    def direct_only(self) -> EdgeQuery:
        """Filter to only DIRECT edges.

        Returns:
            Filtered EdgeQuery with only DIRECT nature edges
        """
        return self.with_nature(EdgeNature.DIRECT)

    def that(self, predicate: Callable[[FunctionEdge], bool]) -> EdgeQuery:
        """Filter by custom predicate.

        Args:
            predicate: Function returning True for matching edges

        Returns:
            Filtered EdgeQuery
        """
        return self._with_filter(predicate)

    def should(self) -> EdgeAssertion:
        """Transition to assertion mode.

        Executes filters and returns assertion builder.

        Returns:
            EdgeAssertion with filtered edges
        """
        edges = execute_query(self._graph.edges, self._filters)
        return EdgeAssertion(_edges=edges)

    def execute(self) -> tuple[FunctionEdge, ...]:
        """Execute query and return matching edges.

        Returns:
            Tuple of edges matching all filters
        """
        return execute_query(self._graph.edges, self._filters)


@dataclass(frozen=True, slots=True)
class EdgeAssertion:
    """Immutable assertion builder for edges.

    Supports chaining assertions before execution.
    """

    _edges: tuple[FunctionEdge, ...]
    _checks: tuple[Callable[[FunctionEdge], Violation | None], ...] = ()

    def _with_check(
        self,
        check: Callable[[FunctionEdge], Violation | None],
    ) -> EdgeAssertion:
        """Return new assertion with additional check.

        Args:
            check: Check function

        Returns:
            New EdgeAssertion with added check (immutable)
        """
        return EdgeAssertion(
            _edges=self._edges,
            _checks=(*self._checks, check),
        )

    def not_cross_boundary(self) -> EdgeAssertion:
        """Assert edges don't cross layer boundaries.

        Returns:
            Assertion with added check
        """
        return self._with_check(make_edge_not_cross_boundary_check())

    def be_allowed(
        self,
        allowed_imports: Mapping[str, frozenset[str]],
    ) -> EdgeAssertion:
        """Assert edges are allowed by layer rules.

        Args:
            allowed_imports: Layer -> allowed target layers mapping

        Returns:
            Assertion with added check

        Raises:
            TypeError: If allowed_imports is None
        """
        if allowed_imports is None:
            raise TypeError("allowed_imports must not be None")
        return self._with_check(make_edge_be_allowed_check(allowed_imports))

    def collect(self) -> tuple[Violation, ...]:
        """Execute checks and return violations.

        Returns:
            Tuple of all violations found
        """
        return execute_checks(self._edges, self._checks)

    def assert_check(self) -> None:
        """Execute checks and raise on violations.

        Raises:
            ArchitectureViolationError: If any violations found
        """
        violations = self.collect()
        if violations:
            raise ArchitectureViolationError(violations)

    def is_valid(self) -> bool:
        """Check if all assertions pass.

        Returns:
            True if no violations, False otherwise
        """
        return len(self.collect()) == 0

    @property
    def edge_count(self) -> int:
        """Number of edges being checked."""
        return len(self._edges)
