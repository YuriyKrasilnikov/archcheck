#ifndef TRACKING_OUTPUT_H
#define TRACKING_OUTPUT_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string.h>
#include "types.h"

/* ============================================================================
 * Output errors tracking
 *
 * Errors that occur during serialization (in stop()) are collected separately.
 * ============================================================================ */

typedef struct {
    char context[64];    /* "event[42].file", "event[42].errors[0].message" */
    char exc_type[ERROR_TYPE_LEN];
    char exc_msg[ERROR_MSG_LEN];
} OutputError;

#define MAX_OUTPUT_ERRORS 64

typedef struct {
    OutputError errors[MAX_OUTPUT_ERRORS];
    int count;
} OutputErrors;

static inline void output_error(OutputErrors *oe, const char *context) {
    if (!oe || oe->count >= MAX_OUTPUT_ERRORS) return;
    if (!PyErr_Occurred()) return;

    PyObject *type, *value, *tb;
    PyErr_Fetch(&type, &value, &tb);

    OutputError *err = &oe->errors[oe->count];

    strncpy(err->context, context, sizeof(err->context) - 1);
    err->context[sizeof(err->context) - 1] = '\0';

    err->exc_type[0] = '\0';
    if (type) {
        const char *name = ((PyTypeObject*)type)->tp_name;
        if (name) {
            strncpy(err->exc_type, name, ERROR_TYPE_LEN - 1);
            err->exc_type[ERROR_TYPE_LEN - 1] = '\0';
        }
    }

    err->exc_msg[0] = '\0';
    if (value) {
        PyObject *str = PyObject_Str(value);
        if (str) {
            const char *msg = PyUnicode_AsUTF8(str);
            if (msg) {
                strncpy(err->exc_msg, msg, ERROR_MSG_LEN - 1);
                err->exc_msg[ERROR_MSG_LEN - 1] = '\0';
            }
            Py_DECREF(str);
            PyErr_Clear();
        }
    }

    oe->count++;

    Py_XDECREF(type);
    Py_XDECREF(value);
    Py_XDECREF(tb);
}

/* ============================================================================
 * Dict helpers with error capture
 * ============================================================================ */

static inline void dict_set_string(PyObject *dict, const char *key, const char *val,
                                   OutputErrors *oe, const char *ctx) {
    if (val == nullptr) {
        Py_INCREF(Py_None);
        PyDict_SetItemString(dict, key, Py_None);
        Py_DECREF(Py_None);
        return;
    }

    PyObject *tmp = PyUnicode_FromString(val);
    if (!tmp) {
        output_error(oe, ctx);
        Py_INCREF(Py_None);
        PyDict_SetItemString(dict, key, Py_None);
        Py_DECREF(Py_None);
        return;
    }

    PyDict_SetItemString(dict, key, tmp);
    Py_DECREF(tmp);
}

static inline void dict_set_long(PyObject *dict, const char *key, long val) {
    PyObject *tmp = PyLong_FromLong(val);
    if (tmp) {
        PyDict_SetItemString(dict, key, tmp);
        Py_DECREF(tmp);
    }
}

static inline void dict_set_ulonglong(PyObject *dict, const char *key, unsigned long long val) {
    PyObject *tmp = PyLong_FromUnsignedLongLong(val);
    if (tmp) {
        PyDict_SetItemString(dict, key, tmp);
        Py_DECREF(tmp);
    }
}

/* ============================================================================
 * Serialization functions
 * ============================================================================ */

static inline PyObject* frame_info_to_dict(const FrameInfo *info, OutputErrors *oe, const char *prefix) {
    if (!info || (!info->file && !info->func && info->line == 0)) {
        Py_RETURN_NONE;
    }

    PyObject *dict = PyDict_New();
    if (!dict) return nullptr;

    char ctx[128];

    snprintf(ctx, sizeof(ctx), "%s.file", prefix);
    dict_set_string(dict, "file", info->file, oe, ctx);

    dict_set_long(dict, "line", info->line);

    snprintf(ctx, sizeof(ctx), "%s.func", prefix);
    dict_set_string(dict, "func", info->func, oe, ctx);

    return dict;
}

static inline PyObject* creation_info_to_dict(const CreationInfo *info, OutputErrors *oe, const char *prefix) {
    if (!info) {
        Py_RETURN_NONE;
    }

    PyObject *dict = PyDict_New();
    if (!dict) return nullptr;

    char ctx[128];

    snprintf(ctx, sizeof(ctx), "%s.file", prefix);
    dict_set_string(dict, "file", info->location.file, oe, ctx);

    dict_set_long(dict, "line", info->location.line);

    snprintf(ctx, sizeof(ctx), "%s.func", prefix);
    dict_set_string(dict, "func", info->location.func, oe, ctx);

    snprintf(ctx, sizeof(ctx), "%s.type", prefix);
    dict_set_string(dict, "type", info->type_name_ref, oe, ctx);

    /* Traceback */
    PyObject *tb = PyList_New(info->traceback_depth);
    if (tb) {
        for (int i = 0; i < info->traceback_depth; i++) {
            char frame_prefix[128];
            snprintf(frame_prefix, sizeof(frame_prefix), "%s.traceback[%d]", prefix, i);
            PyObject *frame = frame_info_to_dict(&info->traceback[i], oe, frame_prefix);
            if (frame) {
                PyList_SET_ITEM(tb, i, frame);
            } else {
                Py_INCREF(Py_None);
                PyList_SET_ITEM(tb, i, Py_None);
            }
        }
        PyDict_SetItemString(dict, "traceback", tb);
        Py_DECREF(tb);
    }

    return dict;
}

static inline PyObject* output_errors_to_list(const OutputErrors *oe) {
    if (!oe || oe->count == 0) {
        Py_RETURN_NONE;
    }

    PyObject *list = PyList_New(oe->count);
    if (!list) return nullptr;

    for (int i = 0; i < oe->count; i++) {
        PyObject *err_dict = PyDict_New();
        if (err_dict) {
            /* These are already validated strings from C, should not fail */
            PyObject *ctx = PyUnicode_FromString(oe->errors[i].context);
            PyObject *type = PyUnicode_FromString(oe->errors[i].exc_type);
            PyObject *msg = PyUnicode_FromString(oe->errors[i].exc_msg);

            if (ctx) { PyDict_SetItemString(err_dict, "context", ctx); Py_DECREF(ctx); }
            if (type) { PyDict_SetItemString(err_dict, "type", type); Py_DECREF(type); }
            if (msg) { PyDict_SetItemString(err_dict, "message", msg); Py_DECREF(msg); }

            PyList_SET_ITEM(list, i, err_dict);
        } else {
            Py_INCREF(Py_None);
            PyList_SET_ITEM(list, i, Py_None);
        }
    }

    return list;
}

/* ============================================================================
 * Event serialization (single responsibility: Event → PyDict)
 * ============================================================================ */

/**
 * Serialize base fields: event, file, line, func.
 * Common to all event types.
 */
static inline void serialize_event_base(PyObject *entry, const Event *evt,
                                        size_t idx, OutputErrors *oe) {
    char ctx[CTX_BUFFER_SIZE];

    (void)snprintf(ctx, sizeof(ctx), "events[%zu].event", idx);
    dict_set_string(entry, "event", event_type_name(evt->type), oe, ctx);

    (void)snprintf(ctx, sizeof(ctx), "events[%zu].file", idx);
    dict_set_string(entry, "file", evt->location.file, oe, ctx);

    dict_set_long(entry, "line", evt->location.line);

    (void)snprintf(ctx, sizeof(ctx), "events[%zu].func", idx);
    dict_set_string(entry, "func", evt->location.func, oe, ctx);
}

/**
 * Serialize lifecycle fields: id, type, creation.
 * For CREATE and DESTROY events.
 */
static inline void serialize_lifecycle_fields(PyObject *entry, const Event *evt,
                                              size_t idx, OutputErrors *oe) {
    char ctx[CTX_BUFFER_SIZE];

    dict_set_ulonglong(entry, "id", evt->obj_id);

    (void)snprintf(ctx, sizeof(ctx), "events[%zu].type", idx);
    dict_set_string(entry, "type", evt->type_name_ref, oe, ctx);

    /* DESTROY: include creation context */
    if (evt->type == EVENT_DESTROY && evt->creation_info) {
        (void)snprintf(ctx, sizeof(ctx), "events[%zu].creation", idx);
        PyObject *creation = creation_info_to_dict(evt->creation_info, oe, ctx);
        if (creation) {
            PyDict_SetItemString(entry, "creation", creation);
            Py_DECREF(creation);
        }
    }
}

/**
 * Serialize CALL fields: caller_file/line/func, args.
 */
static inline void serialize_call_fields(PyObject *entry, const Event *evt,
                                         size_t idx, OutputErrors *oe) {
    char ctx[CTX_BUFFER_SIZE];

    /* Caller info */
    if (evt->caller.func) {
        (void)snprintf(ctx, sizeof(ctx), "events[%zu].caller_file", idx);
        dict_set_string(entry, "caller_file", evt->caller.file, oe, ctx);

        dict_set_long(entry, "caller_line", evt->caller.line);

        (void)snprintf(ctx, sizeof(ctx), "events[%zu].caller_func", idx);
        dict_set_string(entry, "caller_func", evt->caller.func, oe, ctx);
    }

    /* Arguments */
    if (evt->arg_count > 0) {
        PyObject *args_list = PyList_New(evt->arg_count);
        if (args_list) {
            for (int j = 0; j < evt->arg_count; j++) {
                PyObject *arg_dict = PyDict_New();
                if (arg_dict) {
                    (void)snprintf(ctx, sizeof(ctx), "events[%zu].args[%d].name", idx, j);
                    dict_set_string(arg_dict, "name", evt->args[j].name_owned, oe, ctx);

                    dict_set_ulonglong(arg_dict, "id", evt->args[j].id);

                    (void)snprintf(ctx, sizeof(ctx), "events[%zu].args[%d].type", idx, j);
                    dict_set_string(arg_dict, "type", evt->args[j].type_ref, oe, ctx);

                    PyList_SET_ITEM(args_list, j, arg_dict);
                } else {
                    Py_INCREF(Py_None);
                    PyList_SET_ITEM(args_list, j, Py_None);
                }
            }
            PyDict_SetItemString(entry, "args", args_list);
            Py_DECREF(args_list);
        }
    }
}

/**
 * Serialize RETURN fields: return_id, return_type.
 */
static inline void serialize_return_fields(PyObject *entry, const Event *evt,
                                           size_t idx, OutputErrors *oe) {
    char ctx[CTX_BUFFER_SIZE];

    if (evt->obj_id) {
        dict_set_ulonglong(entry, "return_id", evt->obj_id);

        (void)snprintf(ctx, sizeof(ctx), "events[%zu].return_type", idx);
        dict_set_string(entry, "return_type", evt->type_name_ref, oe, ctx);
    }
}

/**
 * Serialize event field errors.
 */
static inline void serialize_event_errors(PyObject *entry, const Event *evt,
                                          size_t idx, OutputErrors *oe) {
    char ctx[CTX_BUFFER_SIZE];

    if (evt->error_count == 0) {
        return;
    }

    PyObject *errors_list = PyList_New(evt->error_count);
    if (!errors_list) {
        return;
    }

    for (int j = 0; j < evt->error_count; j++) {
        PyObject *err_dict = PyDict_New();
        if (err_dict) {
            (void)snprintf(ctx, sizeof(ctx), "events[%zu].errors[%d]", idx, j);
            dict_set_string(err_dict, "field", evt->errors[j].field, oe, ctx);
            dict_set_string(err_dict, "type", evt->errors[j].exc_type, oe, ctx);
            dict_set_string(err_dict, "message", evt->errors[j].exc_msg, oe, ctx);
            PyList_SET_ITEM(errors_list, j, err_dict);
        } else {
            Py_INCREF(Py_None);
            PyList_SET_ITEM(errors_list, j, Py_None);
        }
    }

    PyDict_SetItemString(entry, "errors", errors_list);
    Py_DECREF(errors_list);
}

/**
 * Serialize single event to PyDict.
 * Dispatcher: delegates to type-specific serializers.
 *
 * @return New reference to PyDict, or nullptr on allocation failure.
 */
static inline PyObject* serialize_event(const Event *evt, size_t idx, OutputErrors *oe) {
    PyObject *entry = PyDict_New();
    if (!entry) {
        return nullptr;
    }

    /* Base fields (all events) */
    serialize_event_base(entry, evt, idx, oe);

    /* Type-specific fields */
    switch (evt->type) {
        case EVENT_CREATE:
        case EVENT_DESTROY:
            serialize_lifecycle_fields(entry, evt, idx, oe);
            break;
        case EVENT_CALL:
            serialize_call_fields(entry, evt, idx, oe);
            break;
        case EVENT_RETURN:
            serialize_return_fields(entry, evt, idx, oe);
            break;
    }

    /* Field errors */
    serialize_event_errors(entry, evt, idx, oe);

    return entry;
}

#endif /* TRACKING_OUTPUT_H */
