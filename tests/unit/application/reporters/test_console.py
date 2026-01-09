"""Tests for ConsoleReporter.

Tests:
- ConsoleConfig default values and customization
- ConsoleReporter report() output format
- Event filtering (max_events, include_types, exclude_paths)
- Strategy integration (group_by)
- Lifecycle section rendering
"""

from archcheck.application.reporters.console import ConsoleConfig, ConsoleReporter
from archcheck.application.reporters.strategies import ByFileStrategy, ByFuncStrategy
from archcheck.domain.events import EventType
from tests.factories import (
    make_call_event,
    make_create_event,
    make_creation_info,
    make_destroy_event,
    make_location,
    make_output_error,
    make_return_event,
    make_tracking_result,
)


class TestConsoleConfig:
    """Tests for ConsoleConfig."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        config = ConsoleConfig()
        assert config.show_lifecycle is True
        assert config.show_traceback is True
        assert config.max_events is None
        assert config.group_by is None
        assert config.include_types is None
        assert config.exclude_paths == ()
        assert config.width == 120

    def test_custom_values(self) -> None:
        """Custom values can be set."""
        config = ConsoleConfig(
            show_lifecycle=False,
            show_traceback=False,
            max_events=100,
            group_by=ByFileStrategy(),
            include_types=frozenset({EventType.CALL}),
            exclude_paths=("*.pyc",),
            width=80,
        )
        assert config.show_lifecycle is False
        assert config.max_events == 100
        assert config.include_types == frozenset({EventType.CALL})
        assert config.width == 80


class TestConsoleReporter:
    """Tests for ConsoleReporter."""

    def test_report_contains_header(self) -> None:
        """report() contains TRACKING RESULT header."""
        reporter = ConsoleReporter()
        result = make_tracking_result()
        output = reporter.report(result)
        assert "TRACKING RESULT" in output

    def test_report_contains_event_count(self) -> None:
        """report() shows total event count."""
        reporter = ConsoleReporter()
        result = make_tracking_result(events=(make_call_event(), make_return_event()))
        output = reporter.report(result)
        assert "Events:" in output
        assert "2" in output

    def test_report_with_call_events(self) -> None:
        """report() renders CALL events section."""
        reporter = ConsoleReporter()
        result = make_tracking_result(events=(make_call_event(func="test_function"),))
        output = reporter.report(result)
        assert "CALL EVENTS" in output
        assert "test_function" in output

    def test_report_with_return_events(self) -> None:
        """report() renders RETURN events section."""
        reporter = ConsoleReporter()
        result = make_tracking_result(events=(make_return_event(return_type="MyType"),))
        output = reporter.report(result)
        assert "RETURN EVENTS" in output
        assert "MyType" in output

    def test_report_with_create_events(self) -> None:
        """report() renders CREATE events section."""
        reporter = ConsoleReporter()
        result = make_tracking_result(events=(make_create_event(type_name="Widget"),))
        output = reporter.report(result)
        assert "CREATE EVENTS" in output
        assert "Widget" in output

    def test_report_with_output_errors(self) -> None:
        """report() renders OUTPUT ERRORS section."""
        reporter = ConsoleReporter()
        result = make_tracking_result(
            output_errors=(make_output_error(exc_type="TestError", exc_msg="test message"),),
        )
        output = reporter.report(result)
        assert "OUTPUT ERRORS" in output
        assert "TestError" in output
        assert "test message" in output


class TestConsoleReporterFiltering:
    """Tests for ConsoleReporter filtering."""

    def test_max_events_limits_output(self) -> None:
        """max_events limits number of displayed events."""
        config = ConsoleConfig(max_events=1)
        reporter = ConsoleReporter(config)
        result = make_tracking_result(
            events=(
                make_call_event(line=1),
                make_call_event(line=2),
                make_call_event(line=3),
            ),
        )
        output = reporter.report(result)
        assert "Events:" in output
        assert "1" in output

    def test_include_types_filters_events(self) -> None:
        """include_types filters to specified event types only."""
        config = ConsoleConfig(include_types=frozenset({EventType.CALL}))
        reporter = ConsoleReporter(config)
        result = make_tracking_result(
            events=(make_call_event(), make_return_event(), make_create_event()),
        )
        output = reporter.report(result)
        assert "CALL EVENTS" in output
        assert "RETURN EVENTS" not in output
        assert "CREATE EVENTS" not in output

    def test_exclude_paths_filters_events(self) -> None:
        """exclude_paths filters out matching file paths."""
        config = ConsoleConfig(exclude_paths=("excluded/*",))
        reporter = ConsoleReporter(config)
        result = make_tracking_result(
            events=(
                make_call_event(file="included/kept.py"),
                make_call_event(file="excluded/removed.py"),
            ),
        )
        output = reporter.report(result)
        # Only non-excluded file should appear
        assert "kept.py" in output
        assert "removed.py" not in output


class TestConsoleReporterStrategy:
    """Tests for ConsoleReporter with different strategies."""

    def test_default_strategy_is_by_type(self) -> None:
        """Default strategy groups by event type."""
        reporter = ConsoleReporter()
        result = make_tracking_result(events=(make_call_event(),))
        output = reporter.report(result)
        assert "CALL EVENTS" in output

    def test_by_file_strategy(self) -> None:
        """ByFileStrategy groups by file path."""
        config = ConsoleConfig(group_by=ByFileStrategy())
        reporter = ConsoleReporter(config)
        result = make_tracking_result(events=(make_call_event(file="myfile.py"),))
        output = reporter.report(result)
        assert "myfile.py" in output

    def test_by_func_strategy(self) -> None:
        """ByFuncStrategy groups by function name."""
        config = ConsoleConfig(group_by=ByFuncStrategy())
        reporter = ConsoleReporter(config)
        result = make_tracking_result(events=(make_call_event(func="my_function"),))
        output = reporter.report(result)
        assert "my_function" in output


class TestConsoleReporterLifecycle:
    """Tests for lifecycle rendering."""

    def test_lifecycle_shown_by_default(self) -> None:
        """Lifecycle section shown when CREATE/DESTROY pairs exist."""
        reporter = ConsoleReporter()
        create = make_create_event(obj_id=100, type_name="Widget")
        destroy = make_destroy_event(obj_id=100, type_name="Widget")
        result = make_tracking_result(events=(create, destroy))
        output = reporter.report(result)
        assert "OBJECT LIFECYCLE" in output
        assert "Widget" in output

    def test_lifecycle_hidden_when_disabled(self) -> None:
        """Lifecycle section hidden when show_lifecycle=False."""
        config = ConsoleConfig(show_lifecycle=False)
        reporter = ConsoleReporter(config)
        create = make_create_event(obj_id=100, type_name="Widget")
        destroy = make_destroy_event(obj_id=100, type_name="Widget")
        result = make_tracking_result(events=(create, destroy))
        output = reporter.report(result)
        assert "OBJECT LIFECYCLE" not in output

    def test_traceback_shown_when_enabled(self) -> None:
        """Traceback shown when show_traceback=True and creation info exists."""
        config = ConsoleConfig(show_traceback=True)
        reporter = ConsoleReporter(config)
        creation = make_creation_info(
            traceback=(make_location(func="frame1"), make_location(func="frame2")),
        )
        create = make_create_event(obj_id=100)
        destroy = make_destroy_event(obj_id=100, creation=creation)
        result = make_tracking_result(events=(create, destroy))
        output = reporter.report(result)
        assert "Traceback" in output
        assert "frame1" in output
        assert "frame2" in output
