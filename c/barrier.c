/**
 * Stop Barrier Implementation
 *
 * Reference counting + condition variable barrier.
 *
 * Architecture:
 *   g_barrier.active_callbacks — atomic counter, in-flight protected sections
 *   g_barrier.stopping         — atomic flag, prevents new entries
 *   g_barrier.mutex/cond       — barrier synchronization for stop()
 *   tl_callback_depth          — thread-local depth for stop-from-callback detection
 *
 * State Handling:
 *   UNINITIALIZED/DESTROYED: try_enter() returns false, leave() is no-op
 *   ACTIVE:                  normal operation
 *   STOPPING:                try_enter() returns false, leave() signals
 *
 * Memory Ordering:
 *   - stopping: acquire on read, release on write
 *   - active_callbacks: acq_rel on increment/decrement
 *   - Ensures protected section cannot access freed resources
 *
 * C23: constexpr, nullptr, _Atomic, bool
 * POSIX: pthread (TSan-compatible, NOT C11 threads.h)
 */

#include "tracking/barrier.h"
#include "tracking/invariants.h"

#include <pthread.h>
#include <stdatomic.h>

/* ============================================================================
 * Global State
 * ============================================================================ */

typedef struct {
    /* Reference counting */
    _Atomic(int64_t) active_callbacks;

    /* Stop flag */
    _Atomic(bool) stopping;

    /* Barrier synchronization (pthread for TSan compatibility) */
    pthread_mutex_t mutex;
    pthread_cond_t cond;

    /* Lifecycle: true between init() and destroy() */
    bool initialized;
} Barrier;

static Barrier g_barrier = {0};

/* Thread-local depth: detect stop-from-callback, support nested enter/leave */
static _Thread_local int tl_callback_depth = 0;

/* ============================================================================
 * Lifecycle
 * ============================================================================ */

void barrier_init(void) {
    /* Idempotent: no-op if already initialized */
    if (g_barrier.initialized) {
        return;
    }

    atomic_store(&g_barrier.active_callbacks, 0);
    atomic_store(&g_barrier.stopping, false);

    int result = pthread_mutex_init(&g_barrier.mutex, nullptr);
    REQUIRE(result == 0, "pthread_mutex_init failed");

    result = pthread_cond_init(&g_barrier.cond, nullptr);
    REQUIRE(result == 0, "pthread_cond_init failed");

    g_barrier.initialized = true;
}

void barrier_destroy(void) {
    /* Idempotent: no-op if not initialized */
    if (!g_barrier.initialized) {
        return;
    }

    pthread_mutex_destroy(&g_barrier.mutex);
    pthread_cond_destroy(&g_barrier.cond);

    g_barrier.initialized = false;
}

/* ============================================================================
 * Protected Section API
 * ============================================================================ */

bool barrier_try_enter(void) {
    /*
     * Graceful: return false if not initialized.
     * This is a valid runtime state (after destroy), not a programming error.
     * Frame evaluators may call try_enter() after stop() destroyed the barrier.
     */
    if (!g_barrier.initialized) {
        return false;
    }

    /* Fast path: already stopping */
    if (atomic_load_explicit(&g_barrier.stopping, memory_order_acquire)) {
        return false;
    }

    /* Increment BEFORE entering protected section (acquire-release) */
    atomic_fetch_add_explicit(&g_barrier.active_callbacks, 1, memory_order_acq_rel);

    /*
     * Double-check after increment (handle race with stop).
     * Scenario: stop() set flag between our check and increment.
     * Must decrement and return false.
     */
    if (atomic_load_explicit(&g_barrier.stopping, memory_order_acquire)) {
        int64_t prev = atomic_fetch_sub_explicit(
            &g_barrier.active_callbacks, 1, memory_order_acq_rel);

        /* Signal stop waiter if we were the last one */
        if (prev == 1) {
            pthread_cond_signal(&g_barrier.cond);
        }
        return false;
    }

    tl_callback_depth++;
    return true;
}

void barrier_leave(void) {
    /*
     * Graceful: no-op if not initialized.
     * This handles "late leave" after stop() destroyed the barrier.
     * Scenario: frame evaluator called try_enter(), then Python called stop(),
     * stop() called destroy(), now frame evaluator calls leave().
     * This is valid runtime behavior, not a programming error.
     */
    if (!g_barrier.initialized) {
        return;
    }

    /*
     * FAIL-FIRST: mismatched enter/leave is a programming error.
     * If depth == 0, caller called leave() without successful try_enter().
     */
    REQUIRE(tl_callback_depth > 0, "barrier_leave without barrier_try_enter");

    tl_callback_depth--;

    /* Decrement AFTER leaving protected section (release) */
    int64_t prev = atomic_fetch_sub_explicit(
        &g_barrier.active_callbacks, 1, memory_order_acq_rel);

    /* Signal stop waiter if count reaches 0 during stopping */
    if (prev == 1 && atomic_load_explicit(&g_barrier.stopping, memory_order_acquire)) {
        pthread_cond_signal(&g_barrier.cond);
    }
}

StopResult barrier_stop(void) {
    /*
     * FAIL-FIRST: detect stop() from within callback.
     * Thread-local depth > 0 means current thread is inside try_enter/leave.
     * Calling stop() here would deadlock (waiting for self to leave).
     */
    if (tl_callback_depth > 0) {
        return STOP_FROM_CALLBACK;
    }

    /*
     * Graceful: return STOP_OK if not initialized.
     * Idempotent: stop() after destroy() is valid (no-op).
     */
    if (!g_barrier.initialized) {
        return STOP_OK;
    }

    pthread_mutex_lock(&g_barrier.mutex);

    /* Idempotent: already stopping, return success */
    if (atomic_load_explicit(&g_barrier.stopping, memory_order_acquire)) {
        pthread_mutex_unlock(&g_barrier.mutex);
        return STOP_OK;
    }

    /* Signal: no new entries accepted */
    atomic_store_explicit(&g_barrier.stopping, true, memory_order_release);

    /* Wait: all in-flight protected sections complete */
    while (atomic_load_explicit(&g_barrier.active_callbacks, memory_order_acquire) > 0) {
        pthread_cond_wait(&g_barrier.cond, &g_barrier.mutex);
    }

    /* NOW SAFE: active_callbacks == 0, no new entries possible */
    pthread_mutex_unlock(&g_barrier.mutex);

    return STOP_OK;
}

/* ============================================================================
 * Dispatch API
 * ============================================================================ */

void barrier_dispatch(BarrierCallback cb, void* user_data) {
    /* nullptr callback = no-op */
    if (cb == nullptr) {
        return;
    }

    if (barrier_try_enter()) {
        cb(user_data);
        barrier_leave();
    }
}

/* ============================================================================
 * Query API
 * ============================================================================ */

bool barrier_is_stopping(void) {
    /* Graceful: return false if not initialized */
    if (!g_barrier.initialized) {
        return false;
    }
    return atomic_load_explicit(&g_barrier.stopping, memory_order_acquire);
}

int64_t barrier_active_count(void) {
    /* Graceful: return 0 if not initialized */
    if (!g_barrier.initialized) {
        return 0;
    }
    return atomic_load_explicit(&g_barrier.active_callbacks, memory_order_acquire);
}

bool barrier_in_callback(void) {
    return tl_callback_depth > 0;
}
