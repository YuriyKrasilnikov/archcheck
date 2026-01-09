"""Philosophy compliance tests.

Tests verifying adherence to PHILOSOPHY.md axioms:
- Axiom 7: FAIL-FIRST Validation
- Axiom 8: Immutability
- Axiom 4: Data Completeness
"""

from __future__ import annotations

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
from archcheck.domain.events import (
    CallEvent,
    CreateEvent,
    DestroyEvent,
    Location,
    ReturnEvent,
)
from archcheck.domain.exceptions import (
    AlreadyActiveError,
    ArchCheckError,
    ArchCheckSignal,
    CallbackError,
    ConversionError,
    NotExitedError,
    ParseError,
    StopFromCallbackError,
    StopTracking,
)
from archcheck.domain.graphs import CallEdge, CallGraph, FilterConfig, ObjectFlow
from archcheck.domain.merged_graph import EdgeNature, MergedCallEdge, MergedCallGraph
from archcheck.domain.static_graph import (
    CallType,
    StaticCallEdge,
    StaticCallGraph,
    UnresolvedCall,
)

# =============================================================================
# Axiom 7: FAIL-FIRST Validation
# =============================================================================


class TestFailFirstValidation:
    """Tests for FAIL-FIRST validation.

    PHILOSOPHY.md Axiom 7:
    "WRONG: if not valid: use_default()  # silent fallback
     RIGHT: if not valid: raise InvalidPatternError(...)  # immediate failure"
    """

    def test_import_negative_level_raises(self) -> None:
        """Import with negative level raises ValueError."""
        with pytest.raises(ValueError, match="level"):
            Import(
                module="os",
                name=None,
                alias=None,
                is_relative=False,
                level=-1,
            )

    def test_import_relative_zero_level_raises(self) -> None:
        """Relative import with level 0 raises ValueError."""
        with pytest.raises(ValueError, match="level"):
            Import(
                module="foo",
                name="bar",
                alias=None,
                is_relative=True,
                level=0,
            )

    def test_import_absolute_nonzero_level_raises(self) -> None:
        """Absolute import with level > 0 raises ValueError."""
        with pytest.raises(ValueError, match="level"):
            Import(
                module="os",
                name=None,
                alias=None,
                is_relative=False,
                level=1,
            )

    def test_call_edge_zero_count_raises(self) -> None:
        """CallEdge with count 0 raises ValueError."""
        loc = Location(file="test.py", line=1, func="test")
        with pytest.raises(ValueError, match="count"):
            CallEdge(
                caller=loc,
                callee=loc,
                count=0,
            )

    def test_call_edge_negative_count_raises(self) -> None:
        """CallEdge with negative count raises ValueError."""
        loc = Location(file="test.py", line=1, func="test")
        with pytest.raises(ValueError, match="count"):
            CallEdge(
                caller=loc,
                callee=loc,
                count=-1,
            )

    def test_merged_edge_neither_source_raises(self) -> None:
        """MergedCallEdge with neither static nor runtime raises."""
        with pytest.raises(ValueError, match="at least one"):
            MergedCallEdge(
                caller_fqn="a.foo",
                callee_fqn="b.bar",
                nature=EdgeNature.BOTH,
                static=None,
                runtime=None,
            )

    def test_codebase_module_key_mismatch_raises(self) -> None:
        """Codebase with mismatched module key raises ValueError."""
        module = Module(
            name="actual_name",
            path=None,
            imports=(),
            functions=(),
            classes=(),
            docstring=None,
        )
        with pytest.raises(ValueError, match="key"):
            Codebase(
                root_path=Path(),
                root_package="pkg",
                modules={"wrong_key": module},
            )

    def test_conversion_error_has_details(self) -> None:
        """ConversionError includes expected and got types."""
        error = ConversionError(expected="dict", got=list)
        assert "dict" in str(error)
        assert "list" in str(error)
        assert error.expected == "dict"
        assert error.got is list

    def test_parse_error_has_path(self) -> None:
        """ParseError includes file path."""
        error = ParseError(path="/path/to/file.py", reason="syntax error")
        assert "/path/to/file.py" in str(error)
        assert "syntax error" in str(error)
        assert error.path == "/path/to/file.py"

    def test_already_active_error_message(self) -> None:
        """AlreadyActiveError has fixed message."""
        error = AlreadyActiveError()
        assert "already active" in str(error).lower()

    def test_not_exited_error_message(self) -> None:
        """NotExitedError has fixed message."""
        error = NotExitedError()
        assert "not exited" in str(error).lower()

    def test_stop_from_callback_error_message(self) -> None:
        """StopFromCallbackError has descriptive message."""
        error = StopFromCallbackError()
        assert "callback" in str(error).lower()

    def test_callback_error_preserves_original(self) -> None:
        """CallbackError preserves original exception."""
        original = ValueError("test")
        error = CallbackError(original)
        assert error.original is original
        assert error.__cause__ is original


# =============================================================================
# Axiom 8: Immutability
# =============================================================================


class TestImmutability:
    """Tests for immutability.

    PHILOSOPHY.md Axiom 8:
    "WRONG: categories['test'] = new_value  # mutable
     RIGHT: categories = EntryPointCategories(...)  # immutable"
    """

    def test_location_frozen(self) -> None:
        """Location is frozen dataclass."""
        loc = Location(file="test.py", line=1, func="test")
        with pytest.raises(AttributeError):
            loc.file = "other.py"  # type: ignore[misc]

    def test_call_event_frozen(self) -> None:
        """CallEvent is frozen dataclass."""
        event = CallEvent(
            location=Location(file="test.py", line=1, func="test"),
            caller=None,
            args=(),
            errors=(),
        )
        with pytest.raises(AttributeError):
            event.caller = Location(file="x.py", line=1, func="x")  # type: ignore[misc]

    def test_return_event_frozen(self) -> None:
        """ReturnEvent is frozen dataclass."""
        event = ReturnEvent(
            location=Location(file="test.py", line=1, func="test"),
            return_id=None,
            return_type="int",
        )
        with pytest.raises(AttributeError):
            event.return_type = "str"  # type: ignore[misc]

    def test_create_event_frozen(self) -> None:
        """CreateEvent is frozen dataclass."""
        event = CreateEvent(
            location=Location(file="test.py", line=1, func="test"),
            obj_id=12345,
            type_name="list",
        )
        with pytest.raises(AttributeError):
            event.type_name = "dict"  # type: ignore[misc]

    def test_destroy_event_frozen(self) -> None:
        """DestroyEvent is frozen dataclass."""
        event = DestroyEvent(
            location=Location(file="test.py", line=1, func="test"),
            obj_id=12345,
            type_name="list",
            creation=None,
        )
        with pytest.raises(AttributeError):
            event.obj_id = 99999  # type: ignore[misc]

    def test_call_edge_frozen(self) -> None:
        """CallEdge is frozen dataclass."""
        loc = Location(file="test.py", line=1, func="test")
        edge = CallEdge(caller=loc, callee=loc, count=1)
        with pytest.raises(AttributeError):
            edge.count = 2  # type: ignore[misc]

    def test_static_call_edge_frozen(self) -> None:
        """StaticCallEdge is frozen dataclass."""
        edge = StaticCallEdge(
            caller_fqn="a.foo",
            callee_fqn="b.bar",
            call_type=CallType.DIRECT,
            location=Location(file="a.py", line=1, func="foo"),
        )
        with pytest.raises(AttributeError):
            edge.call_type = CallType.METHOD  # type: ignore[misc]

    def test_merged_call_edge_frozen(self) -> None:
        """MergedCallEdge is frozen dataclass."""
        static = StaticCallEdge(
            caller_fqn="a.foo",
            callee_fqn="b.bar",
            call_type=CallType.DIRECT,
            location=Location(file="a.py", line=1, func="foo"),
        )
        edge = MergedCallEdge(
            caller_fqn="a.foo",
            callee_fqn="b.bar",
            nature=EdgeNature.STATIC_ONLY,
            static=static,
            runtime=None,
        )
        with pytest.raises(AttributeError):
            edge.nature = EdgeNature.BOTH  # type: ignore[misc]

    def test_import_frozen(self) -> None:
        """Import is frozen dataclass."""
        imp = Import(
            module="os",
            name=None,
            alias=None,
            is_relative=False,
            level=0,
        )
        with pytest.raises(AttributeError):
            imp.module = "sys"  # type: ignore[misc]

    def test_parameter_frozen(self) -> None:
        """Parameter is frozen dataclass."""
        param = Parameter(
            name="x",
            kind=ParameterKind.POSITIONAL_OR_KEYWORD,
            annotation=None,
            default=None,
        )
        with pytest.raises(AttributeError):
            param.name = "y"  # type: ignore[misc]

    def test_function_frozen(self) -> None:
        """Function is frozen dataclass."""
        func = Function(
            name="foo",
            qualified_name="mod.foo",
            parameters=(),
            return_annotation=None,
            location=Location(file="mod.py", line=1, func="foo"),
            is_async=False,
            is_generator=False,
            is_method=False,
            decorators=(),
            body_calls=(),
        )
        with pytest.raises(AttributeError):
            func.name = "bar"  # type: ignore[misc]

    def test_class_frozen(self) -> None:
        """Class is frozen dataclass."""
        cls = Class(
            name="Foo",
            qualified_name="mod.Foo",
            bases=(),
            methods=(),
            is_protocol=False,
            is_dataclass=False,
            location=Location(file="mod.py", line=1, func=None),
        )
        with pytest.raises(AttributeError):
            cls.name = "Bar"  # type: ignore[misc]

    def test_module_frozen(self) -> None:
        """Module is frozen dataclass."""
        mod = Module(
            name="mymod",
            path=None,
            imports=(),
            functions=(),
            classes=(),
            docstring=None,
        )
        with pytest.raises(AttributeError):
            mod.name = "other"  # type: ignore[misc]

    def test_codebase_frozen(self) -> None:
        """Codebase is frozen dataclass."""
        codebase = Codebase(
            root_path=Path(),
            root_package="pkg",
            modules={},
        )
        with pytest.raises(AttributeError):
            codebase.modules = {"x": None}  # type: ignore[misc]

    def test_filter_config_frozen(self) -> None:
        """FilterConfig is frozen dataclass."""
        config = FilterConfig()
        with pytest.raises(AttributeError):
            config.include_paths = ("new/*",)  # type: ignore[misc]

    def test_unresolved_call_frozen(self) -> None:
        """UnresolvedCall is frozen dataclass."""
        call = UnresolvedCall(
            caller_fqn="a.foo",
            callee_name="unknown",
            reason="undefined",
            location=Location(file="a.py", line=1, func="foo"),
        )
        with pytest.raises(AttributeError):
            call.reason = "other"  # type: ignore[misc]


# =============================================================================
# Axiom 4: Data Completeness
# =============================================================================


class TestDataCompleteness:
    """Tests for data completeness.

    PHILOSOPHY.md Axiom 4:
    "WRONG: Entry points not matching patterns -> lost
     RIGHT: Entry points not matching patterns -> tracked in .uncategorized
     Invariant: all_entry_points = categorized U uncategorized"
    """

    def test_call_graph_tracks_unmatched(self) -> None:
        """CallGraph tracks unmatched events."""
        loc = Location(file="test.py", line=1, func="test")
        edge = CallEdge(caller=loc, callee=loc, count=1)
        unmatched_event = CallEvent(
            location=loc,
            caller=None,
            args=(),
            errors=(),
        )

        graph = CallGraph(
            edges=(edge,),
            unmatched=(unmatched_event,),
        )

        # All data accessible
        assert len(graph.edges) == 1
        assert len(graph.unmatched) == 1
        assert graph.unmatched[0] is unmatched_event

    def test_object_flow_tracks_orphans(self) -> None:
        """ObjectFlow tracks orphan destroy events."""
        loc = Location(file="test.py", line=1, func="test")
        orphan = DestroyEvent(
            location=loc,
            obj_id=12345,
            type_name="list",
            creation=None,
        )

        flow = ObjectFlow(
            objects={},
            orphan_destroys=(orphan,),
        )

        # Orphan data accessible
        assert len(flow.orphan_destroys) == 1
        assert flow.orphan_destroys[0] is orphan

    def test_static_graph_tracks_unresolved(self) -> None:
        """StaticCallGraph tracks unresolved calls."""
        edge = StaticCallEdge(
            caller_fqn="a.foo",
            callee_fqn="b.bar",
            call_type=CallType.DIRECT,
            location=Location(file="a.py", line=1, func="foo"),
        )
        unresolved = UnresolvedCall(
            caller_fqn="a.foo",
            callee_name="unknown",
            reason="undefined",
            location=Location(file="a.py", line=2, func="foo"),
        )

        graph = StaticCallGraph(
            edges=(edge,),
            unresolved=(unresolved,),
        )

        # Both resolved and unresolved accessible
        assert len(graph.edges) == 1
        assert len(graph.unresolved) == 1
        assert graph.unresolved[0] is unresolved

    def test_merged_graph_preserves_both_sources(self) -> None:
        """MergedCallGraph preserves both static and runtime data."""
        static_edge = StaticCallEdge(
            caller_fqn="a.foo",
            callee_fqn="b.bar",
            call_type=CallType.DIRECT,
            location=Location(file="a.py", line=1, func="foo"),
        )
        runtime_edge = CallEdge(
            caller=Location(file="a.py", line=1, func="foo"),
            callee=Location(file="b.py", line=1, func="bar"),
            count=1,
        )

        merged = MergedCallEdge(
            caller_fqn="a.foo",
            callee_fqn="b.bar",
            nature=EdgeNature.BOTH,
            static=static_edge,
            runtime=runtime_edge,
        )

        graph = MergedCallGraph(
            edges=(merged,),
            nodes=frozenset(["a.foo", "b.bar"]),
            by_caller={"a.foo": frozenset(["b.bar"])},
            by_callee={"b.bar": frozenset(["a.foo"])},
            by_nature={EdgeNature.BOTH: (merged,)},
        )

        # Both sources accessible
        assert graph.edges[0].static is static_edge
        assert graph.edges[0].runtime is runtime_edge


# =============================================================================
# Signal vs Error Distinction
# =============================================================================


class TestSignalErrorDistinction:
    """Tests for proper signal vs error classification.

    StopTracking is a signal (flow control), like StopIteration.
    Both inherit from Exception (Python convention for signals).
    """

    def test_stop_tracking_is_signal(self) -> None:
        """StopTracking inherits from ArchCheckSignal."""
        assert issubclass(StopTracking, ArchCheckSignal)

    def test_stop_tracking_not_archcheck_error(self) -> None:
        """StopTracking is NOT an ArchCheckError (it's a signal)."""
        assert not issubclass(StopTracking, ArchCheckError)

    def test_archcheck_errors_are_exceptions(self) -> None:
        """ArchCheckError subclasses are proper Exceptions."""
        assert issubclass(ParseError, ArchCheckError)
        assert issubclass(ParseError, Exception)
        assert issubclass(ConversionError, ArchCheckError)
        assert issubclass(AlreadyActiveError, ArchCheckError)

    def test_signal_and_error_disjoint(self) -> None:
        """Signals and errors are disjoint hierarchies."""
        # No type is both signal and error
        assert not issubclass(ArchCheckSignal, ArchCheckError)
        assert not issubclass(ArchCheckError, ArchCheckSignal)

    def test_stop_tracking_can_be_caught_separately(self) -> None:
        """StopTracking can be caught separately from errors."""
        caught_signal = False
        caught_error = False

        try:
            raise StopTracking
        except ArchCheckError:
            caught_error = True
        except ArchCheckSignal:
            caught_signal = True

        assert caught_signal
        assert not caught_error
