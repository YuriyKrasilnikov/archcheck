#ifndef TRACKING_ERRORS_H
#define TRACKING_ERRORS_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string.h>
#include <stdio.h>
#include "types.h"

/**
 * Capture current Python exception into event's error list.
 * Clears the exception after capturing.
 *
 * @param ev    Event to add error to
 * @param field Field name that caused the error (e.g., "file", "func", "arg[0]")
 */
static inline void capture_error(Event *ev, const char *field) {
    if (!ev || ev->error_count >= MAX_FIELD_ERRORS) return;
    if (!PyErr_Occurred()) return;

    PyObject *type, *value, *tb;
    PyErr_Fetch(&type, &value, &tb);

    FieldError *err = &ev->errors[ev->error_count];

    /* Field name */
    strncpy(err->field, field, ERROR_FIELD_LEN - 1);
    err->field[ERROR_FIELD_LEN - 1] = '\0';

    /* Exception type */
    err->exc_type[0] = '\0';
    if (type) {
        const char *name = ((PyTypeObject*)type)->tp_name;
        if (name) {
            strncpy(err->exc_type, name, ERROR_TYPE_LEN - 1);
            err->exc_type[ERROR_TYPE_LEN - 1] = '\0';
        }
    }

    /* Exception message */
    err->exc_msg[0] = '\0';
    if (value) {
        PyObject *str = PyObject_Str(value);
        if (str) {
            const char *msg = PyUnicode_AsUTF8(str);
            if (msg) {
                strncpy(err->exc_msg, msg, ERROR_MSG_LEN - 1);
                err->exc_msg[ERROR_MSG_LEN - 1] = '\0';
            } else {
                /* Can't decode error message itself - meta error */
                PyErr_Clear();
                strncpy(err->exc_msg, "<message decode failed>", ERROR_MSG_LEN - 1);
            }
            Py_DECREF(str);
        }
    }

    ev->error_count++;

    Py_XDECREF(type);
    Py_XDECREF(value);
    Py_XDECREF(tb);
}

/**
 * Try to get UTF-8 string, capture error if fails.
 * Returns pointer to Python internal buffer - valid only while object alive.
 *
 * @param obj   Python unicode object
 * @param ev    Event to capture error into (can be nullptr to skip capture)
 * @param field Field name for error reporting
 * @return      UTF-8 string or nullptr on error
 */
static inline const char* safe_utf8(PyObject *obj, Event *ev, const char *field) {
    if (!obj) return nullptr;
    if (!PyUnicode_Check(obj)) return nullptr;

    const char *result = PyUnicode_AsUTF8(obj);
    if (!result && ev) {
        capture_error(ev, field);
    }
    return result;
}

/**
 * Copy UTF-8 string from Python object.
 * Returns heap-allocated copy that must be freed with free().
 * Safe to use after Python object is garbage collected.
 *
 * @param obj   Python unicode object
 * @param ev    Event to capture error into (can be nullptr to skip capture)
 * @param field Field name for error reporting
 * @return      Heap-allocated string copy or nullptr on error
 */
static inline char* copy_utf8(PyObject *obj, Event *ev, const char *field) {
    const char *tmp = safe_utf8(obj, ev, field);
    if (!tmp) return nullptr;
    return strdup(tmp);
}

#endif /* TRACKING_ERRORS_H */
