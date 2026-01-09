/**
 * Event Callback Implementation
 *
 * Integrates StringTable and Stop Barrier for safe event dispatch.
 *
 * Architecture:
 *   g_callback    — user callback function
 *   g_user_data   — opaque pointer for callback
 *   g_active      — tracking active flag
 *
 * Uses:
 *   - barrier.c for safe dispatch with reference counting
 *   - interning.c for string interning
 *
 * Note: For context extraction (thread_id, coro_id, timestamp_ns)
 *       use context.h directly.
 *
 * C23: constexpr, nullptr, _Atomic
 */

#include "tracking/callback.h"
#include "tracking/interning.h"
#include "tracking/invariants.h"

#include <stdatomic.h>

/* ============================================================================
 * Global State
 * ============================================================================ */

static EventCallback g_callback = nullptr;
static void* g_user_data = nullptr;
static _Atomic(bool) g_active = false;

/* ============================================================================
 * Internal: Dispatch Wrapper
 * ============================================================================ */

typedef struct {
    const RawEvent* event;
} DispatchContext;

static void dispatch_wrapper(void* user_data) {
    DispatchContext* ctx = (DispatchContext*)user_data;

    if (g_callback != nullptr && ctx->event != nullptr) {
        g_callback(ctx->event, g_user_data);
    }
}

/* ============================================================================
 * Public API
 * ============================================================================ */

void tracking_start(EventCallback cb, void* user_data) {
    /* Initialize dependencies */
    string_table_init(0);  /* Default capacity */
    barrier_init();

    /* Register callback */
    g_callback = cb;
    g_user_data = user_data;
    atomic_store(&g_active, true);
}

StopResult tracking_stop(void) {
    /* Already stopped */
    if (!atomic_load(&g_active)) {
        return STOP_OK;
    }

    /* Stop barrier (waits for in-flight callbacks) */
    StopResult result = barrier_stop();
    if (result != STOP_OK) {
        return result;
    }

    /* Clear callback */
    g_callback = nullptr;
    g_user_data = nullptr;
    atomic_store(&g_active, false);

    /* Destroy string table (invalidates all interned strings) */
    string_table_destroy();
    barrier_destroy();

    return STOP_OK;
}

bool tracking_is_active(void) {
    return atomic_load(&g_active);
}

void tracking_dispatch(const RawEvent* event) {
    if (event == nullptr) {
        return;
    }

    if (!atomic_load(&g_active)) {
        return;
    }

    DispatchContext ctx = {.event = event};
    barrier_dispatch(dispatch_wrapper, &ctx);
}
