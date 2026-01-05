"""Test factories: create domain objects for tests."""

from archcheck.domain.events import (
    ArgInfo,
    CallEvent,
    CreateEvent,
    CreationInfo,
    DestroyEvent,
    FieldError,
    Location,
    OutputError,
    ReturnEvent,
    TrackingResult,
)


def make_location(
    file: str | None = "test.py",
    line: int = 1,
    func: str | None = "test_func",
) -> Location:
    """Create Location with defaults."""
    return Location(file=file, line=line, func=func)


def make_call_event(
    file: str | None = "test.py",
    line: int = 10,
    func: str | None = "call_func",
    caller_file: str | None = "caller.py",
    caller_line: int = 5,
    caller_func: str | None = "caller_func",
    args: tuple[ArgInfo, ...] = (),
    errors: tuple[FieldError, ...] = (),
) -> CallEvent:
    """Create CallEvent with defaults."""
    caller = Location(file=caller_file, line=caller_line, func=caller_func)
    return CallEvent(
        location=Location(file=file, line=line, func=func),
        caller=caller,
        args=args,
        errors=errors,
    )


def make_return_event(
    file: str | None = "test.py",
    line: int = 20,
    func: str | None = "return_func",
    return_id: int | None = 12345,
    return_type: str | None = "str",
) -> ReturnEvent:
    """Create ReturnEvent with defaults."""
    return ReturnEvent(
        location=Location(file=file, line=line, func=func),
        return_id=return_id,
        return_type=return_type,
    )


def make_create_event(
    file: str | None = "test.py",
    line: int = 30,
    func: str | None = "create_func",
    obj_id: int = 100,
    type_name: str = "TestClass",
) -> CreateEvent:
    """Create CreateEvent with defaults."""
    return CreateEvent(
        location=Location(file=file, line=line, func=func),
        obj_id=obj_id,
        type_name=type_name,
    )


def make_destroy_event(
    file: str | None = "test.py",
    line: int = 40,
    func: str | None = "destroy_func",
    obj_id: int = 100,
    type_name: str = "TestClass",
    creation: CreationInfo | None = None,
) -> DestroyEvent:
    """Create DestroyEvent with defaults."""
    return DestroyEvent(
        location=Location(file=file, line=line, func=func),
        obj_id=obj_id,
        type_name=type_name,
        creation=creation,
    )


def make_creation_info(
    file: str | None = "test.py",
    line: int = 30,
    func: str | None = "create_func",
    type_name: str | None = "TestClass",
    traceback: tuple[Location, ...] = (),
) -> CreationInfo:
    """Create CreationInfo with defaults."""
    return CreationInfo(
        location=Location(file=file, line=line, func=func),
        type_name=type_name,
        traceback=traceback,
    )


def make_arg_info(
    name: str | None = "arg",
    obj_id: int = 1,
    type_name: str | None = "int",
) -> ArgInfo:
    """Create ArgInfo with defaults."""
    return ArgInfo(name=name, obj_id=obj_id, type_name=type_name)


def make_output_error(
    context: str = "test_context",
    exc_type: str = "TestError",
    exc_msg: str = "test error message",
) -> OutputError:
    """Create OutputError with defaults."""
    return OutputError(context=context, exc_type=exc_type, exc_msg=exc_msg)


def make_tracking_result(
    events: tuple[CallEvent | ReturnEvent | CreateEvent | DestroyEvent, ...] = (),
    output_errors: tuple[OutputError, ...] = (),
) -> TrackingResult:
    """Create TrackingResult with defaults."""
    return TrackingResult(events=events, output_errors=output_errors)
