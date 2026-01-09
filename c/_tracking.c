/**
 * Data flow tracking via PyRefTracer + Frame Eval Hook.
 *
 * Architecture:
 *   - C stores EVERYTHING, no filtering
 *   - Hash table: obj_id → creation_info (with full traceback)
 *   - DESTROY event includes BOTH creation_ctx AND destruction_ctx
 *   - All errors captured with full exception info
 *   - Python does all filtering
 *
 * Requires: Python 3.14+ (PyRefTracer API)
 */

#define PY_SSIZE_T_CLEAN
#define Py_BUILD_CORE
#include <Python.h>
#include <frameobject.h>
#include <string.h>
#include <stdlib.h>
#include "internal/pycore_frame.h"
#include "internal/pycore_interpframe_structs.h"
#include "internal/pycore_stackref.h"
#include "internal/pycore_ceval.h"

#include "tracking/types.h"
#include "tracking/memory.h"
#include "tracking/errors.h"
#include "tracking/hashtable.h"
#include "tracking/events.h"
#include "tracking/output.h"

/* New module: thread-safe barrier for safe termination */
#include "tracking/barrier.h"

/* Execution context: thread_id, coro_id, timestamp_ns */
#include "tracking/context.h"

/* ============================================================================
 * Python Runtime Context Implementation
 *
 * context_coro_id() and context_task_id() are declared in context.h
 * but require Python.h access, so implemented here.
 * ============================================================================ */

uint64_t context_coro_id(void) {
    PyThreadState *tstate = PyThreadState_Get();
    if (tstate == nullptr) {
        return 0;
    }

    _PyInterpreterFrame *frame = tstate->current_frame;
    if (frame == nullptr) {
        return 0;
    }

    _PyStackRef exec_ref = frame->f_executable;
    if (PyStackRef_IsNull(exec_ref)) {
        return 0;
    }

    PyObject *executable = PyStackRef_AsPyObjectBorrow(exec_ref);
    if (PyCoro_CheckExact(executable) || PyAsyncGen_CheckExact(executable)) {
        return (uint64_t)executable;
    }

    return 0;
}

uint64_t context_task_id(void) {
    /* Phase 5 stub: asyncio task tracking not implemented.
     * Full implementation requires asyncio.current_task() C API. */
    return 0;
}

/* ============================================================================
 * Global state
 * ============================================================================ */

static _PyFrameEvalFunction original_eval = nullptr;

static inline PyObject* invoke_original_eval(
    PyThreadState *tstate, _PyInterpreterFrame *frame, int throwflag)
{
    if (original_eval) {
        return original_eval(tstate, frame, throwflag);
    }
    return _PyEval_EvalFrameDefault(tstate, frame, throwflag);
}

static creation_map obj_creation_map;
static __thread FrameInfo call_stack[MAX_STACK_DEPTH];
static __thread int stack_depth = 0;

static Event *events = nullptr;
static size_t events_count = 0;
static size_t events_capacity = 0;
static int tracking_active = 0;

/* ============================================================================
 * Event registry
 * ============================================================================ */

static int ensure_events_capacity(size_t needed) {
    if (events_count + needed <= events_capacity) {
        return 1;
    }

    size_t new_capacity = events_capacity == 0
        ? INITIAL_EVENTS_CAPACITY
        : events_capacity * 2;

    while (new_capacity < events_count + needed) {
        new_capacity *= 2;
    }

    Event *new_events = realloc(events, new_capacity * sizeof(Event));
    if (!new_events) {
        return 0;
    }

    events = new_events;
    events_capacity = new_capacity;
    return 1;
}

static void free_events(void) {
    if (events) {
        for (size_t i = 0; i < events_count; i++) {
            Event *evt = &events[i];
            free_frame_info(&evt->location);
            free_frame_info(&evt->caller);
            for (int j = 0; j < evt->arg_count; j++) {
                free(evt->args[j].name_owned);
                evt->args[j].name_owned = nullptr;
            }
            if (evt->creation_info) {
                free(evt->creation_info);
                evt->creation_info = nullptr;
            }
        }
        free(events);
    }
    events = nullptr;
    events_count = 0;
    events_capacity = 0;
}

/* ============================================================================
 * Frame Eval Hook
 * ============================================================================ */

static PyObject* tracking_frame_evaluator(
    PyThreadState *tstate,
    _PyInterpreterFrame *frame,
    int throwflag)
{
    if (!tracking_active) {
        goto call_original;
    }

    /* CRITICAL: Enter barrier-protected section.
     * This prevents use-after-free when py_stop() called during eval. */
    if (!barrier_try_enter()) {
        goto call_original;  /* Stopping, skip tracking */
    }

    /* Get code object */
    _PyStackRef exec_ref = frame->f_executable;
    if (PyStackRef_IsNull(exec_ref)) {
        barrier_leave();
        goto call_original;
    }
    PyObject *executable = PyStackRef_AsPyObjectBorrow(exec_ref);
    if (!PyCode_Check(executable)) {
        barrier_leave();
        goto call_original;
    }
    PyCodeObject *code = (PyCodeObject *)executable;

    /* Ensure space for CALL + RETURN */
    if (!ensure_events_capacity(2)) {
        barrier_leave();
        goto call_original;
    }

    /* Record CALL event */
    Event *call_event = &events[events_count++];
    memset(call_event, 0, sizeof(Event));
    const FrameInfo *caller = stack_depth > 0 ? &call_stack[stack_depth - 1] : nullptr;
    fill_call_event(call_event, code, frame, caller);

    /* Push to call stack */
    if (stack_depth < MAX_STACK_DEPTH) {
        call_stack[stack_depth] = call_event->location;
        stack_depth++;
    }

    /* Save location locally BEFORE original_eval.
     * After original_eval events may be realloc'd or freed. */
    FrameInfo saved_location = call_event->location;

    /* Leave barrier before calling original eval (allows nested calls).
     * Re-enter after to record RETURN event. */
    barrier_leave();

    /* Call original evaluator (may be long-running, allows py_stop()) */
    PyObject *result = invoke_original_eval(tstate, frame, throwflag);

    /* Pop from call stack */
    if (stack_depth > 0) {
        stack_depth--;
    }

    /* Re-enter barrier for RETURN event */
    if (!barrier_try_enter()) {
        /* Stopping during eval, skip RETURN event */
        return result;
    }

    /* Safety: stop() may have been called during original_eval. */
    if (!tracking_active || !events) {
        barrier_leave();
        return result;
    }

    /* Re-check capacity (nested calls may have consumed it) */
    if (!ensure_events_capacity(1)) {
        barrier_leave();
        return result;
    }

    /* Record RETURN event */
    Event *ret_event = &events[events_count++];
    memset(ret_event, 0, sizeof(Event));
    fill_return_event(ret_event, &saved_location, result);

    barrier_leave();
    return result;

call_original:
    return invoke_original_eval(tstate, frame, throwflag);
}

/* ============================================================================
 * PyRefTracer handlers (separated for single responsibility)
 * ============================================================================ */

/**
 * Handle object creation: store in hash table and record event.
 */
static void handle_ref_create(uintptr_t obj_id, const char *type_name) {
    /* Store creation info in hash table */
    CreationInfo empty_info = {0};
    creation_map_itr itr = vt_insert(&obj_creation_map, obj_id, empty_info);

    if (!vt_is_end(itr)) {
        CreationInfo *info = &itr.data->val;
        info->type_name_ref = type_name;

        if (stack_depth > 0) {
            info->location = call_stack[stack_depth - 1];

            /* Capture full traceback */
            int depth = stack_depth < MAX_TRACEBACK_DEPTH ? stack_depth : MAX_TRACEBACK_DEPTH;
            info->traceback_depth = depth;
            for (int i = 0; i < depth; i++) {
                info->traceback[i] = call_stack[stack_depth - 1 - i];
            }
        }
    }

    /* Record CREATE event */
    if (!ensure_events_capacity(1)) {
        return;
    }

    Event *ev = &events[events_count++];
    memset(ev, 0, sizeof(Event));
    fill_create_event(ev, obj_id, type_name, call_stack, stack_depth);
}

/**
 * Handle object destruction: lookup creation, record event, cleanup.
 */
static void handle_ref_destroy(uintptr_t obj_id, const char *type_name) {
    /* Lookup creation info */
    creation_map_itr itr = vt_get(&obj_creation_map, obj_id);
    CreationInfo *creation_info = vt_is_end(itr) ? nullptr : &itr.data->val;

    /* Copy creation info to heap BEFORE erasing hash table entry */
    CreationInfo *creation_copy = nullptr;
    if (creation_info) {
        creation_copy = malloc(sizeof(CreationInfo));
        if (creation_copy) {
            *creation_copy = *creation_info;
        }
    }

    /* Record DESTROY event */
    if (ensure_events_capacity(1)) {
        Event *ev = &events[events_count++];
        memset(ev, 0, sizeof(Event));
        fill_destroy_event(ev, obj_id, type_name, call_stack, stack_depth, creation_copy);
    } else if (creation_copy) {
        free(creation_copy);
    }

    /* Remove from hash table */
    if (!vt_is_end(itr)) {
        vt_erase_itr(&obj_creation_map, itr);
    }
}

/* ============================================================================
 * PyRefTracer callback
 * ============================================================================ */

static int ref_tracer_callback(PyObject *obj, PyRefTracerEvent event, void *data) {
    (void)data;

    if (!tracking_active) {
        return 0;
    }

    /* Enter barrier-protected section */
    if (!barrier_try_enter()) {
        return 0;  /* Stopping, skip tracking */
    }

    uintptr_t obj_id = (uintptr_t)obj;
    const char *type_name = Py_TYPE(obj)->tp_name;

    switch (event) {
        case PyRefTracer_CREATE:
            handle_ref_create(obj_id, type_name);
            break;
        case PyRefTracer_DESTROY:
            handle_ref_destroy(obj_id, type_name);
            break;
    }

    barrier_leave();
    return 0;
}

/* ============================================================================
 * Python API
 * ============================================================================ */

static PyObject* py_start(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;

    if (tracking_active) {
        PyErr_SetString(PyExc_RuntimeError, "Already started");
        return nullptr;
    }

    /* Clear previous state */
    free_events();
    vt_cleanup(&obj_creation_map);
    vt_init(&obj_creation_map);
    stack_depth = 0;

    /* Initialize stop barrier for safe termination */
    barrier_init();

    /* Set up frame eval hook */
    PyInterpreterState *interp = PyInterpreterState_Get();
    original_eval = _PyInterpreterState_GetEvalFrameFunc(interp);
    _PyInterpreterState_SetEvalFrameFunc(interp, tracking_frame_evaluator);

    /* Set up PyRefTracer */
    if (PyRefTracer_SetTracer(ref_tracer_callback, nullptr) != 0) {
        _PyInterpreterState_SetEvalFrameFunc(interp, original_eval);
        original_eval = nullptr;
        PyErr_SetString(PyExc_RuntimeError, "Failed to set tracer");
        return nullptr;
    }

    tracking_active = 1;
    Py_RETURN_NONE;
}

static PyObject* py_stop(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;

    if (!tracking_active) {
        PyErr_SetString(PyExc_RuntimeError, "Not started");
        return nullptr;
    }

    tracking_active = 0;

    /* CRITICAL: Wait for all in-flight frame evaluations via barrier.
     * This prevents use-after-free when stop() called during callback. */
    StopResult stop_result = barrier_stop();
    if (stop_result == STOP_FROM_CALLBACK) {
        /* Cannot stop from within a tracked function call */
        tracking_active = 1;  /* Restore state */
        PyErr_SetString(PyExc_RuntimeError, "Cannot stop() from tracked callback");
        return nullptr;
    }

    /* Restore original frame evaluator */
    PyInterpreterState *interp = PyInterpreterState_Get();
    _PyInterpreterState_SetEvalFrameFunc(interp, original_eval);
    original_eval = nullptr;

    /* Clear PyRefTracer */
    PyRefTracer_SetTracer(nullptr, nullptr);

    /* Destroy barrier NOW — all hooks disabled, no more callbacks possible */
    barrier_destroy();

    /* Track output errors */
    OutputErrors output_errors = {0};

    /* Build result */
    PyObject *result_dict = PyDict_New();
    if (!result_dict) {
        free_events();
        vt_cleanup(&obj_creation_map);
        return nullptr;
    }

    PyObject *events_list = PyList_New(0);
    if (!events_list) {
        Py_DECREF(result_dict);
        free_events();
        vt_cleanup(&obj_creation_map);
        return nullptr;
    }

    for (size_t i = 0; i < events_count; i++) {
        PyObject *entry = serialize_event(&events[i], i, &output_errors);
        if (entry) {
            PyList_Append(events_list, entry);
            Py_DECREF(entry);
        }
    }

    PyDict_SetItemString(result_dict, "events", events_list);
    Py_DECREF(events_list);

    /* Output errors */
    if (output_errors.count > 0) {
        PyObject *oe_list = output_errors_to_list(&output_errors);
        if (oe_list) {
            PyDict_SetItemString(result_dict, "output_errors", oe_list);
            Py_DECREF(oe_list);
        }
    }

    free_events();
    vt_cleanup(&obj_creation_map);
    /* barrier already destroyed after hooks disabled (line 375) */
    return result_dict;
}

static PyObject* py_count(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    return PyLong_FromSize_t(events_count);
}

static PyObject* py_is_active(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    return PyBool_FromLong(tracking_active);
}

static PyObject* py_get_origin(PyObject *self, PyObject *args) {
    (void)self;

    PyObject *obj;
    if (!PyArg_ParseTuple(args, "O", &obj)) {
        return nullptr;
    }

    if (!tracking_active) {
        PyErr_SetString(PyExc_RuntimeError, "Tracking not active");
        return nullptr;
    }

    uintptr_t obj_id = (uintptr_t)obj;
    creation_map_itr itr = vt_get(&obj_creation_map, obj_id);

    if (vt_is_end(itr)) {
        Py_RETURN_NONE;
    }

    OutputErrors oe = {0};
    return creation_info_to_dict(&itr.data->val, &oe, "origin");
}

/* ============================================================================
 * Module
 * ============================================================================ */

static PyMethodDef methods[] = {
    {"start", py_start, METH_NOARGS,
     "Start tracking. Captures all events, no filtering."},
    {"stop", py_stop, METH_NOARGS,
     "Stop tracking and return {events: [...], output_errors: [...]}"},
    {"count", py_count, METH_NOARGS,
     "Current event count"},
    {"is_active", py_is_active, METH_NOARGS,
     "Is tracking active"},
    {"get_origin", py_get_origin, METH_VARARGS,
     "Get creation info for object (while tracking is active)"},
    {nullptr, nullptr, 0, nullptr}
};

/**
 * Module exec function for multi-phase init.
 * Called after module object is created.
 */
static int module_exec(PyObject *module) {
    (void)module;
    vt_init(&obj_creation_map);
    return 0;
}

/**
 * Module slots for Python 3.14+ free-threading support.
 *
 * Current: Py_MOD_GIL_USED (safe default, GIL re-enabled on module load)
 *
 * PREREQUISITE for Py_MOD_GIL_NOT_USED (full free-threaded support):
 *   1. C atomics: DONE (barrier.c, interning.c)
 *   2. SafeCallback._lock: DONE (PHASE01 Section 1.6)
 *   3. Per-thread builders: PHASE02 Section 2.5 (builder.py)
 *
 * Without per-thread builders, parallel callbacks race on shared OMEGABuilder.
 * See: tests/unit/infrastructure/test_free_threaded_builder.py
 *
 * TODO(PHASE02 step 12): After builder.py → Py_MOD_GIL_NOT_USED
 */
static PyModuleDef_Slot module_slots[] = {
    {Py_mod_exec, module_exec},
    {Py_mod_gil, Py_MOD_GIL_USED},
    {0, nullptr}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "_tracking",
    "Data flow tracking with full error capture",
    0,              /* m_size: 0 for multi-phase init */
    methods,
    module_slots,   /* m_slots */
    nullptr,        /* m_traverse */
    nullptr,        /* m_clear */
    nullptr         /* m_free */
};

PyMODINIT_FUNC PyInit__tracking(void) {
    return PyModuleDef_Init(&module);
}
