#ifndef TRACKING_TYPES_H
#define TRACKING_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include "constants.h"

/* ============================================================================
 * C23 static_assert for compile-time invariants
 * ============================================================================ */

static_assert(MAX_ARGS > 0, "MAX_ARGS must be positive");
static_assert(MAX_TRACEBACK_DEPTH > 0, "MAX_TRACEBACK_DEPTH must be positive");
static_assert(MAX_STACK_DEPTH > 0, "MAX_STACK_DEPTH must be positive");
static_assert(MAX_FIELD_ERRORS > 0, "MAX_FIELD_ERRORS must be positive");
static_assert(ERROR_MSG_LEN >= 64, "ERROR_MSG_LEN too small");
static_assert(ERROR_FIELD_LEN >= 16, "ERROR_FIELD_LEN too small");
static_assert(CTX_BUFFER_SIZE >= 64, "CTX_BUFFER_SIZE too small for context strings");

/* ============================================================================
 * Frame location
 * ============================================================================ */

typedef struct {
    char *file;  /* Heap-allocated, must free */
    int line;
    char *func;  /* Heap-allocated, must free */
} FrameInfo;

/* ============================================================================
 * Error captured during event processing
 * ============================================================================ */

typedef struct {
    char field[ERROR_FIELD_LEN];    /* "file", "func", "arg[0]" */
    char exc_type[ERROR_TYPE_LEN];  /* "UnicodeDecodeError" */
    char exc_msg[ERROR_MSG_LEN];    /* full message */
} FieldError;

/* ============================================================================
 * Creation info stored in hash table
 * ============================================================================ */

typedef struct {
    FrameInfo location;
    FrameInfo traceback[MAX_TRACEBACK_DEPTH];
    int traceback_depth;
    const char *type_name_ref;  /* Borrowed from tp_name, do NOT free */
} CreationInfo;

/* ============================================================================
 * Argument info for CALL events
 * ============================================================================ */

typedef struct {
    char *name_owned;           /* Heap-allocated via strdup, must free */
    uintptr_t id;
    const char *type_ref;       /* Borrowed from tp_name, do NOT free */
} ArgInfo;

/* ============================================================================
 * Event types
 * ============================================================================ */

typedef enum {
    EVENT_CALL,
    EVENT_RETURN,
    EVENT_CREATE,
    EVENT_DESTROY
} EventType;

/**
 * Convert EventType to string.
 * FAIL-FIRST: unreachable() on invalid type.
 */
static inline const char* event_type_name(EventType ev) {
    switch (ev) {
        case EVENT_CALL:    return "CALL";
        case EVENT_RETURN:  return "RETURN";
        case EVENT_CREATE:  return "CREATE";
        case EVENT_DESTROY: return "DESTROY";
    }
    unreachable();
}

/* ============================================================================
 * Event record
 * ============================================================================ */

typedef struct {
    EventType type;
    uintptr_t obj_id;
    const char *type_name_ref;  /* Borrowed from tp_name, do NOT free */

    /* Location of this event */
    FrameInfo location;

    /* For CALL: caller info */
    FrameInfo caller;

    /* For CALL: arguments */
    ArgInfo args[MAX_ARGS];
    int arg_count;

    /* For DESTROY: where object was created */
    CreationInfo *creation_info;

    /* Errors captured during this event */
    FieldError errors[MAX_FIELD_ERRORS];
    int error_count;
} Event;

#endif /* TRACKING_TYPES_H */
