/**
 * Event Callback Module
 *
 * Defines event types and callback registration for tracking.
 * Uses Stop Barrier for safe dispatch.
 *
 * Contract:
 *   - All string fields in events are INTERNED (pointer stable)
 *   - Callback receives events with valid pointers during call only
 *   - After callback returns, event data may be invalidated
 *   - tracking_stop() waits for all in-flight callbacks
 *
 * C23: constexpr, nullptr, [[nodiscard]], _Atomic
 */

#ifndef TRACKING_CALLBACK_H
#define TRACKING_CALLBACK_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#include "tracking/barrier.h"

/* ============================================================================
 * Event Types
 * ============================================================================ */

/**
 * Event kind enumeration.
 */
typedef enum {
    EVENT_CALL,     /* Function call */
    EVENT_RETURN,   /* Function return */
    EVENT_CREATE,   /* Object creation */
    EVENT_DESTROY,  /* Object destruction */
} EventKind;

/**
 * Raw call event data.
 * All strings INTERNED (valid until string_table_destroy).
 */
typedef struct {
    const char* callee_file;
    int32_t callee_line;
    const char* callee_func;
    const char* caller_file;
    int32_t caller_line;
    const char* caller_func;
    uint64_t thread_id;
    uint64_t coro_id;
    uint64_t timestamp_ns;
} RawCallEvent;

/**
 * Raw return event data.
 */
typedef struct {
    const char* file;
    int32_t line;
    const char* func;
    uint64_t thread_id;
    uint64_t timestamp_ns;
    bool has_exception;
} RawReturnEvent;

/**
 * Raw object creation event.
 */
typedef struct {
    uintptr_t obj_id;
    const char* type_name;  /* Interned */
    const char* file;
    int32_t line;
    const char* func;
    uint64_t thread_id;
    uint64_t timestamp_ns;
} RawCreateEvent;

/**
 * Raw object destruction event.
 */
typedef struct {
    uintptr_t obj_id;
    const char* type_name;  /* Interned */
    uint64_t thread_id;
    uint64_t timestamp_ns;
} RawDestroyEvent;

/**
 * Union of all event types.
 */
typedef struct {
    EventKind kind;
    union {
        RawCallEvent call;
        RawReturnEvent ret;
        RawCreateEvent create;
        RawDestroyEvent destroy;
    } data;
} RawEvent;

/* ============================================================================
 * Callback Types
 * ============================================================================ */

/**
 * Event callback signature.
 *
 * @param event      Event data (valid only during callback).
 * @param user_data  Opaque pointer from tracking_start().
 *
 * IMPORTANT:
 *   - Copy any strings you need BEFORE returning
 *   - Do NOT store event pointer
 *   - Do NOT call tracking_stop() from callback
 */
typedef void (*EventCallback)(const RawEvent* event, void* user_data);

/* ============================================================================
 * Tracking API
 * ============================================================================ */

/**
 * Start tracking with callback.
 *
 * @param cb         Callback to invoke for each event. May be nullptr (no-op).
 * @param user_data  Opaque pointer passed to callback.
 *
 * Initializes:
 *   - StringTable (for interning)
 *   - Stop Barrier (for safe dispatch)
 *
 * FAIL-FIRST: Aborts on allocation failure.
 * Idempotent: Safe to call multiple times (re-registers callback).
 */
void tracking_start(EventCallback cb, void* user_data);

/**
 * Stop tracking and wait for all callbacks.
 *
 * Waits for all in-flight callbacks via Stop Barrier.
 * After return, no more callbacks will be invoked.
 *
 * @return STOP_OK if successful, STOP_FROM_CALLBACK if called from callback.
 *
 * Destroys:
 *   - StringTable (invalidates all interned strings)
 *
 * Idempotent: Safe to call multiple times.
 */
[[nodiscard]]
StopResult tracking_stop(void);

/**
 * Check if tracking is active.
 *
 * @return true if tracking_start() called and tracking_stop() not called.
 */
bool tracking_is_active(void);

/* ============================================================================
 * Event Dispatch (Internal)
 * ============================================================================ */

/**
 * Dispatch event to callback.
 *
 * Uses Stop Barrier for safe dispatch:
 *   1. Check stopping flag
 *   2. Increment active count
 *   3. Double-check after increment
 *   4. Invoke callback
 *   5. Decrement active count
 *
 * @param event  Event to dispatch.
 *
 * Thread-safe: concurrent dispatch OK.
 * If stopping, dispatch is no-op.
 */
void tracking_dispatch(const RawEvent* event);

/* ============================================================================
 * Context Extraction
 *
 * For thread_id, coro_id, timestamp_ns use:
 *   #include "tracking/context.h"
 *
 * Functions: context_thread_id(), context_coro_id(), context_timestamp_ns()
 * ============================================================================ */

#endif /* TRACKING_CALLBACK_H */
