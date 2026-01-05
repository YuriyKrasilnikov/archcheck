"""Tests for JsonReporter.

Tests:
- report() returns valid JSON string
- JSON structure matches domain objects
- Summary statistics calculation
- Event serialization for all event types
- Output errors serialization
"""

import json

from archcheck.application.reporters.json import JsonReporter
from tests.factories import (
    make_arg_info,
    make_call_event,
    make_create_event,
    make_creation_info,
    make_destroy_event,
    make_location,
    make_output_error,
    make_return_event,
    make_tracking_result,
)


class TestJsonReporter:
    """Tests for JsonReporter."""

    def test_report_returns_str(self) -> None:
        """report() returns string."""
        reporter = JsonReporter()
        result = make_tracking_result()
        output = reporter.report(result)
        assert isinstance(output, str)

    def test_report_is_valid_json(self) -> None:
        """report() returns valid JSON."""
        reporter = JsonReporter()
        result = make_tracking_result()
        output = reporter.report(result)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_report_has_required_keys(self) -> None:
        """JSON contains events, output_errors, summary keys."""
        reporter = JsonReporter()
        result = make_tracking_result()
        output = reporter.report(result)
        data = json.loads(output)
        assert "events" in data
        assert "output_errors" in data
        assert "summary" in data

    def test_summary_structure(self) -> None:
        """Summary contains total and by_type counts."""
        reporter = JsonReporter()
        result = make_tracking_result(
            events=(make_call_event(), make_return_event()),
        )
        output = reporter.report(result)
        data = json.loads(output)

        assert data["summary"]["total"] == 2
        assert "by_type" in data["summary"]
        assert data["summary"]["by_type"]["CALL"] == 1
        assert data["summary"]["by_type"]["RETURN"] == 1

    def test_indent_parameter(self) -> None:
        """Indent parameter controls JSON formatting."""
        reporter_indent = JsonReporter(indent=2)
        reporter_compact = JsonReporter(indent=None)

        result = make_tracking_result()
        output_indent = reporter_indent.report(result)
        output_compact = reporter_compact.report(result)

        assert len(output_indent) > len(output_compact)


class TestJsonReporterEvents:
    """Tests for event serialization."""

    def test_call_event_structure(self) -> None:
        """CallEvent serializes with all fields."""
        reporter = JsonReporter()
        event = make_call_event(
            file="test.py",
            line=10,
            func="my_func",
            caller_file="caller.py",
            caller_line=5,
            caller_func="caller_func",
            args=(make_arg_info(name="x", obj_id=1, type_name="int"),),
        )
        result = make_tracking_result(events=(event,))
        output = reporter.report(result)
        data = json.loads(output)

        ev = data["events"][0]
        assert ev["type"] == "CALL"
        assert ev["location"]["file"] == "test.py"
        assert ev["location"]["line"] == 10
        assert ev["location"]["func"] == "my_func"
        assert ev["caller"]["file"] == "caller.py"
        assert ev["caller"]["line"] == 5
        assert ev["args"][0]["name"] == "x"
        assert ev["args"][0]["id"] == 1
        assert ev["args"][0]["type"] == "int"

    def test_return_event_structure(self) -> None:
        """ReturnEvent serializes with all fields."""
        reporter = JsonReporter()
        event = make_return_event(
            file="test.py",
            line=20,
            func="return_func",
            return_id=12345,
            return_type="str",
        )
        result = make_tracking_result(events=(event,))
        output = reporter.report(result)
        data = json.loads(output)

        ev = data["events"][0]
        assert ev["type"] == "RETURN"
        assert ev["location"]["func"] == "return_func"
        assert ev["return_id"] == 12345
        assert ev["return_type"] == "str"

    def test_create_event_structure(self) -> None:
        """CreateEvent serializes with all fields."""
        reporter = JsonReporter()
        event = make_create_event(
            file="test.py",
            line=30,
            func="create_func",
            obj_id=100,
            type_name="MyClass",
        )
        result = make_tracking_result(events=(event,))
        output = reporter.report(result)
        data = json.loads(output)

        ev = data["events"][0]
        assert ev["type"] == "CREATE"
        assert ev["obj_id"] == 100
        assert ev["type_name"] == "MyClass"

    def test_destroy_event_structure(self) -> None:
        """DestroyEvent serializes with creation info."""
        reporter = JsonReporter()
        creation = make_creation_info(
            file="origin.py",
            line=10,
            func="origin_func",
            type_name="MyClass",
            traceback=(make_location(func="frame1"),),
        )
        event = make_destroy_event(
            file="test.py",
            line=40,
            func="destroy_func",
            obj_id=100,
            type_name="MyClass",
            creation=creation,
        )
        result = make_tracking_result(events=(event,))
        output = reporter.report(result)
        data = json.loads(output)

        ev = data["events"][0]
        assert ev["type"] == "DESTROY"
        assert ev["obj_id"] == 100
        assert ev["creation"]["location"]["file"] == "origin.py"
        assert ev["creation"]["traceback"][0]["func"] == "frame1"

    def test_destroy_event_without_creation(self) -> None:
        """DestroyEvent with creation=None serializes correctly."""
        reporter = JsonReporter()
        event = make_destroy_event(creation=None)
        result = make_tracking_result(events=(event,))
        output = reporter.report(result)
        data = json.loads(output)

        ev = data["events"][0]
        assert ev["creation"] is None


class TestJsonReporterErrors:
    """Tests for output_errors serialization."""

    def test_output_error_structure(self) -> None:
        """OutputError serializes with all fields."""
        reporter = JsonReporter()
        error = make_output_error(
            context="serialize",
            exc_type="TypeError",
            exc_msg="cannot serialize",
        )
        result = make_tracking_result(output_errors=(error,))
        output = reporter.report(result)
        data = json.loads(output)

        err = data["output_errors"][0]
        assert err["context"] == "serialize"
        assert err["type"] == "TypeError"
        assert err["message"] == "cannot serialize"

    def test_multiple_errors(self) -> None:
        """Multiple errors are serialized."""
        reporter = JsonReporter()
        result = make_tracking_result(
            output_errors=(
                make_output_error(context="ctx1"),
                make_output_error(context="ctx2"),
            ),
        )
        output = reporter.report(result)
        data = json.loads(output)

        assert len(data["output_errors"]) == 2
