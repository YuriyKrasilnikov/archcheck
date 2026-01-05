#ifndef TRACKING_CONSTANTS_H
#define TRACKING_CONSTANTS_H

#include <stddef.h>

/* ============================================================================
 * C23 constexpr constants
 * ============================================================================ */

/* Traceback depth for creation info */
constexpr int MAX_TRACEBACK_DEPTH = 16;

/* Maximum arguments to capture per call */
constexpr int MAX_ARGS = 8;

/* Maximum call stack depth */
constexpr int MAX_STACK_DEPTH = 256;

/* Maximum errors per event */
constexpr int MAX_FIELD_ERRORS = 8;

/* Error message buffer size */
constexpr int ERROR_MSG_LEN = 256;

/* Error field name buffer size */
constexpr int ERROR_FIELD_LEN = 32;

/* Error type name buffer size */
constexpr int ERROR_TYPE_LEN = 64;

/* Initial event registry size */
constexpr size_t INITIAL_EVENTS_CAPACITY = 4096;

/* Serialization context buffer ("events[999].args[7].type") */
constexpr int CTX_BUFFER_SIZE = 128;

#endif /* TRACKING_CONSTANTS_H */
