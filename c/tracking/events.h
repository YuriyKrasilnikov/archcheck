#ifndef TRACKING_EVENTS_H
#define TRACKING_EVENTS_H

#define PY_SSIZE_T_CLEAN
#define Py_BUILD_CORE
#include <Python.h>
#include <frameobject.h>
#include "internal/pycore_frame.h"
#include "internal/pycore_stackref.h"

#include "types.h"
#include "errors.h"
#include "memory.h"

/* ============================================================================
 * Event filling (single responsibility: fill Event struct)
 *
 * Functions fill Event* without knowing about global event storage.
 * Caller is responsible for:
 *   - Allocating Event (ensure_events_capacity)
 *   - memset(ev, 0, sizeof(Event)) before calling
 *   - Managing event lifetime (free_events)
 * ============================================================================ */

/**
 * Fill CALL event from code object and call stack.
 *
 * @param ev           Pre-zeroed Event to fill
 * @param code         Code object being called
 * @param frame        Interpreter frame with arguments
 * @param caller       Caller location (can be nullptr)
 */
static inline void fill_call_event(
    Event *ev,
    PyCodeObject *code,
    _PyInterpreterFrame *frame,
    const FrameInfo *caller)
{
    ev->type = EVENT_CALL;
    ev->location.line = code->co_firstlineno;

    /* Copy strings - survive frame exit */
    ev->location.file = copy_utf8(code->co_filename, ev, "file");
    ev->location.func = copy_utf8(code->co_qualname, ev, "func");

    /* Caller info */
    if (caller) {
        copy_frame_info(&ev->caller, caller);
    }

    /* Extract arguments */
    _PyStackRef *localsarray = frame->localsplus;
    PyObject *names = code->co_localsplusnames;
    int argcount = code->co_argcount + code->co_kwonlyargcount;
    if (code->co_flags & CO_VARARGS) {
        argcount++;
    }
    if (code->co_flags & CO_VARKEYWORDS) {
        argcount++;
    }
    int max_args = argcount < MAX_ARGS ? argcount : MAX_ARGS;

    for (int i = 0; i < max_args; i++) {
        _PyStackRef ref = localsarray[i];
        if (!PyStackRef_IsNull(ref)) {
            PyObject *value = PyStackRef_AsPyObjectBorrow(ref);
            PyObject *name_obj = PyTuple_GET_ITEM(names, i);

            char field[ERROR_FIELD_LEN];
            (void)snprintf(field, sizeof(field), "arg[%d]", i);

            ev->args[ev->arg_count].name_owned = copy_utf8(name_obj, ev, field);
            ev->args[ev->arg_count].id = (uintptr_t)value;
            ev->args[ev->arg_count].type_ref = Py_TYPE(value)->tp_name;
            ev->arg_count++;
        }
    }
}

/**
 * Fill RETURN event.
 *
 * @param ev           Pre-zeroed Event to fill
 * @param location     Location of the return (copy of call location)
 * @param result       Return value (can be nullptr)
 */
static inline void fill_return_event(
    Event *ev,
    const FrameInfo *location,
    PyObject *result)
{
    ev->type = EVENT_RETURN;

    /* Copy location strings - each event owns its strings */
    copy_frame_info(&ev->location, location);

    if (result) {
        ev->obj_id = (uintptr_t)result;
        ev->type_name_ref = Py_TYPE(result)->tp_name;
    }
}

/**
 * Fill CREATE event.
 *
 * @param ev           Pre-zeroed Event to fill
 * @param obj_id       Object id (uintptr_t cast of PyObject*)
 * @param type_name    Type name (borrowed from tp_name)
 * @param call_stack   Current call stack
 * @param stack_depth  Call stack depth
 */
static inline void fill_create_event(
    Event *ev,
    uintptr_t obj_id,
    const char *type_name,
    const FrameInfo *call_stack,
    int stack_depth)
{
    ev->type = EVENT_CREATE;
    ev->obj_id = obj_id;
    ev->type_name_ref = type_name;

    if (stack_depth > 0) {
        copy_frame_info(&ev->location, &call_stack[stack_depth - 1]);
    }
}

/**
 * Fill DESTROY event.
 *
 * @param ev             Pre-zeroed Event to fill
 * @param obj_id         Object id
 * @param type_name      Type name (borrowed from tp_name)
 * @param call_stack     Current call stack
 * @param stack_depth    Call stack depth
 * @param creation_copy  Heap-allocated CreationInfo (ownership transferred)
 */
static inline void fill_destroy_event(
    Event *ev,
    uintptr_t obj_id,
    const char *type_name,
    const FrameInfo *call_stack,
    int stack_depth,
    CreationInfo *creation_copy)
{
    ev->type = EVENT_DESTROY;
    ev->obj_id = obj_id;
    ev->type_name_ref = type_name;

    /* Destruction context */
    if (stack_depth > 0) {
        copy_frame_info(&ev->location, &call_stack[stack_depth - 1]);
    }

    /* Creation context (ownership transferred) */
    ev->creation_info = creation_copy;
}

#endif /* TRACKING_EVENTS_H */
