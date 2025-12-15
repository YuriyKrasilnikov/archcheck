"""Tests for build_merged_graph."""

import pytest

from archcheck.application.merge.builder import build_merged_graph
from archcheck.domain.model.edge_nature import EdgeNature
from tests.factories import (
    make_call_site,
    make_lib_call_site,
    make_runtime_graph,
    make_static_edge,
    make_static_graph,
)

# Default empty dependencies for build_merged_graph
_EMPTY_IMPORTS: dict[str, frozenset[str]] = {}
_EMPTY_FRAMEWORKS: frozenset[str] = frozenset()


class TestBuildMergedGraphFailFirst:
    """Test FAIL-FIRST validation."""

    def test_none_static_raises(self) -> None:
        """None static raises TypeError."""
        runtime = make_runtime_graph()
        with pytest.raises(TypeError, match="static must not be None"):
            build_merged_graph(
                None,  # type: ignore[arg-type]
                runtime,
                _EMPTY_IMPORTS,
                _EMPTY_FRAMEWORKS,
            )

    def test_none_runtime_raises(self) -> None:
        """None runtime raises TypeError."""
        static = make_static_graph()
        with pytest.raises(TypeError, match="runtime must not be None"):
            build_merged_graph(
                static,
                None,  # type: ignore[arg-type]
                _EMPTY_IMPORTS,
                _EMPTY_FRAMEWORKS,
            )

    def test_none_module_imports_raises(self) -> None:
        """None module_imports raises TypeError."""
        static = make_static_graph()
        runtime = make_runtime_graph()
        with pytest.raises(TypeError, match="module_imports must not be None"):
            build_merged_graph(
                static,
                runtime,
                None,  # type: ignore[arg-type]
                _EMPTY_FRAMEWORKS,
            )

    def test_none_known_frameworks_raises(self) -> None:
        """None known_frameworks raises TypeError."""
        static = make_static_graph()
        runtime = make_runtime_graph()
        with pytest.raises(TypeError, match="known_frameworks must not be None"):
            build_merged_graph(
                static,
                runtime,
                _EMPTY_IMPORTS,
                None,  # type: ignore[arg-type]
            )


class TestBuildMergedGraphEmpty:
    """Test empty graphs."""

    def test_both_empty(self) -> None:
        """Empty graphs produce empty merged graph."""
        static = make_static_graph()
        runtime = make_runtime_graph()

        merged = build_merged_graph(static, runtime, _EMPTY_IMPORTS, _EMPTY_FRAMEWORKS)

        assert merged.node_count == 0
        assert merged.edge_count == 0
        assert merged.lib_edge_count == 0
        assert merged.hidden_dep_count == 0


class TestBuildMergedGraphEdges:
    """Test function edge building."""

    def test_ast_edge_in_runtime_included(self) -> None:
        """Edge present in both AST and runtime is included as FunctionEdge."""
        # AST has edge A → B
        static = make_static_graph(
            edges=frozenset({make_static_edge("myapp.a", "myapp.b")}),
            functions=frozenset({"myapp.a", "myapp.b"}),
        )

        # Runtime has edge A → B
        caller = make_call_site("myapp", "a")
        callee = make_call_site("myapp", "b")
        runtime = make_runtime_graph(
            edges={(caller, callee): 5},
            called_functions=frozenset({caller, callee}),
        )

        # Provide imports so edge is classified as DIRECT
        module_imports = {"myapp": frozenset({"myapp"})}

        merged = build_merged_graph(static, runtime, module_imports, _EMPTY_FRAMEWORKS)

        assert merged.edge_count == 1
        edge = merged.get_edge("myapp.a", "myapp.b")
        assert edge is not None
        assert edge.total_count == 5

    def test_ast_edge_not_in_runtime_excluded(self) -> None:
        """Edge only in AST (not called at runtime) is excluded."""
        # AST has edge A → B
        static = make_static_graph(
            edges=frozenset({make_static_edge("myapp.a", "myapp.b")}),
            functions=frozenset({"myapp.a", "myapp.b"}),
        )

        # Runtime has no edges
        runtime = make_runtime_graph()

        merged = build_merged_graph(static, runtime, _EMPTY_IMPORTS, _EMPTY_FRAMEWORKS)

        assert merged.edge_count == 0


class TestBuildMergedGraphLibEdges:
    """Test library edge building."""

    def test_lib_edges_included(self) -> None:
        """Library edges from runtime are included as LibEdge."""
        static = make_static_graph()

        caller = make_call_site("myapp", "process")
        lib = make_lib_call_site("requests", "get")
        runtime = make_runtime_graph(
            lib_edges={(caller, lib): 3},
            called_functions=frozenset({caller}),
        )

        merged = build_merged_graph(static, runtime, _EMPTY_IMPORTS, _EMPTY_FRAMEWORKS)

        assert merged.lib_edge_count == 1
        # Find lib edge by caller
        lib_edge = next(
            (e for e in merged.lib_edges if e.caller_fqn == "myapp.process"),
            None,
        )
        assert lib_edge is not None
        assert lib_edge.lib_target.lib_name == "requests"
        assert lib_edge.total_count == 3


class TestBuildMergedGraphHiddenDeps:
    """Test hidden dependency detection.

    NOTE: Only DYNAMIC hidden deps exist now.
    FRAMEWORK → EdgeNature.FRAMEWORK in edges
    PARAMETRIC → EdgeNature.PARAMETRIC in edges
    """

    def test_runtime_only_edge_without_import_is_parametric(self) -> None:
        """Runtime-only edge without import is PARAMETRIC (HOF pattern).

        This represents Higher-Order Function pattern where callee
        is passed as parameter, not directly imported.
        """
        # AST has no edges but knows functions exist
        static = make_static_graph(functions=frozenset({"myapp.caller", "myapp.callee"}))

        # Runtime has edge (callee passed as parameter)
        caller = make_call_site("myapp", "caller")
        callee = make_call_site("myapp", "callee")
        runtime = make_runtime_graph(
            edges={(caller, callee): 1},
            called_functions=frozenset({caller, callee}),
        )

        # No imports → will be classified as PARAMETRIC
        merged = build_merged_graph(static, runtime, _EMPTY_IMPORTS, _EMPTY_FRAMEWORKS)

        # Should be in edges with PARAMETRIC nature, NOT in hidden_deps
        assert merged.hidden_dep_count == 0
        assert merged.edge_count == 1
        edge = merged.get_edge("myapp.caller", "myapp.callee")
        assert edge is not None
        assert edge.nature == EdgeNature.PARAMETRIC

    def test_framework_caller_creates_framework_edge(self) -> None:
        """Framework-initiated call creates edge with FRAMEWORK nature.

        When pytest (framework) calls test functions, this is normal
        and should NOT be a boundary violation.
        """
        static = make_static_graph(functions=frozenset({"pytest.runner", "myapp.test_func"}))

        caller = make_call_site("pytest", "runner")
        callee = make_call_site("myapp", "test_func")
        runtime = make_runtime_graph(
            edges={(caller, callee): 1},
            called_functions=frozenset({caller, callee}),
        )

        # pytest is a known framework
        known_frameworks = frozenset({"pytest"})

        merged = build_merged_graph(static, runtime, _EMPTY_IMPORTS, known_frameworks)

        # Should be in edges with FRAMEWORK nature, NOT in hidden_deps
        assert merged.hidden_dep_count == 0
        assert merged.edge_count == 1
        edge = merged.get_edge("pytest.runner", "myapp.test_func")
        assert edge is not None
        assert edge.nature == EdgeNature.FRAMEWORK


class TestBuildMergedGraphNodes:
    """Test node collection."""

    def test_nodes_from_runtime(self) -> None:
        """Nodes are extracted from runtime called_functions."""
        static = make_static_graph()

        site1 = make_call_site("myapp", "func1")
        site2 = make_call_site("myapp", "func2")
        runtime = make_runtime_graph(called_functions=frozenset({site1, site2}))

        merged = build_merged_graph(static, runtime, _EMPTY_IMPORTS, _EMPTY_FRAMEWORKS)

        assert merged.node_count == 2
        assert "myapp.func1" in merged.nodes
        assert "myapp.func2" in merged.nodes


class TestBuildMergedGraphEdgeNature:
    """Test EdgeNature classification."""

    def test_imported_callee_is_direct(self) -> None:
        """Callee imported by caller → DIRECT edge."""
        static = make_static_graph(
            edges=frozenset({make_static_edge("myapp.service", "myapp.repo")}),
            functions=frozenset({"myapp.service", "myapp.repo"}),
        )

        caller = make_call_site("myapp", "service")
        callee = make_call_site("myapp", "repo")
        runtime = make_runtime_graph(
            edges={(caller, callee): 1},
            called_functions=frozenset({caller, callee}),
        )

        # service module imports repo module
        module_imports = {"myapp": frozenset({"myapp"})}

        merged = build_merged_graph(static, runtime, module_imports, _EMPTY_FRAMEWORKS)

        edge = merged.get_edge("myapp.service", "myapp.repo")
        assert edge is not None
        assert edge.nature == EdgeNature.DIRECT
        assert edge.is_boundary_relevant is True

    def test_not_imported_callee_is_parametric(self) -> None:
        """Callee not imported by caller → PARAMETRIC edge (HOF)."""
        static = make_static_graph(
            edges=frozenset({make_static_edge("myapp.service", "myapp.repo")}),
            functions=frozenset({"myapp.service", "myapp.repo"}),
        )

        caller = make_call_site("myapp", "service")
        callee = make_call_site("myapp", "repo")
        runtime = make_runtime_graph(
            edges={(caller, callee): 1},
            called_functions=frozenset({caller, callee}),
        )

        # Empty imports → callee not imported → PARAMETRIC
        merged = build_merged_graph(static, runtime, _EMPTY_IMPORTS, _EMPTY_FRAMEWORKS)

        edge = merged.get_edge("myapp.service", "myapp.repo")
        assert edge is not None
        assert edge.nature == EdgeNature.PARAMETRIC
        assert edge.is_boundary_relevant is False

    def test_framework_caller_is_framework(self) -> None:
        """Framework caller → FRAMEWORK edge."""
        static = make_static_graph(
            edges=frozenset({make_static_edge("fastapi.routing", "myapp.handler")}),
            functions=frozenset({"fastapi.routing", "myapp.handler"}),
        )

        caller = make_call_site("fastapi.routing", "dispatch")
        callee = make_call_site("myapp", "handler")
        runtime = make_runtime_graph(
            edges={(caller, callee): 1},
            called_functions=frozenset({caller, callee}),
        )

        known_frameworks = frozenset({"fastapi"})

        merged = build_merged_graph(static, runtime, _EMPTY_IMPORTS, known_frameworks)

        edge = merged.get_edge("fastapi.routing.dispatch", "myapp.handler")
        assert edge is not None
        assert edge.nature == EdgeNature.FRAMEWORK
        assert edge.is_boundary_relevant is False
