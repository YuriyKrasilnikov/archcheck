/**
 * Stop Barrier
 *
 * Reference counting + condition variable barrier for safe callback termination.
 * Fixes use-after-free in _tracking.c:158.
 *
 * Contract:
 *   - try_enter() increments counter BEFORE protected section
 *   - leave() decrements counter AFTER protected section
 *   - stop() waits until counter == 0 before returning
 *   - destroy() releases resources after stop()
 *   - After destroy(), try_enter() returns false (valid state, not error)
 *
 * State Machine:
 *   [UNINITIALIZED] --init()--> [ACTIVE] --stop()--> [STOPPED] --destroy()--> [DESTROYED]
 *        ^                                                                        |
 *        +------------------------------------------------------------------------+
 *                                    (next init())
 *
 * Destroyed State:
 *   After destroy(), barrier is in DESTROYED state. This is a valid runtime
 *   state, NOT a programming error. Operations gracefully handle this:
 *     - try_enter() returns false
 *     - leave() is no-op
 *     - stop() returns STOP_OK (idempotent)
 *   This allows frame evaluators to handle stop() called during execution.
 *
 * FAIL-FIRST (programming errors only):
 *   - stop() from callback: returns STOP_FROM_CALLBACK (detect via thread-local)
 *   - leave() without enter: aborts (mismatched enter/leave)
 *   - init() failure: aborts (resource allocation)
 *
 * Thread Safety:
 *   - All operations thread-safe
 *   - pthread (NOT C11 threads.h, TSan incompatible)
 *
 * C23: constexpr, nullptr, [[nodiscard]], _Atomic
 */

#ifndef TRACKING_BARRIER_H
#define TRACKING_BARRIER_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

/* ============================================================================
 * Types
 * ============================================================================ */

/**
 * Result of barrier_stop().
 */
typedef enum {
    STOP_OK,              /* Barrier stopped, cleanup safe */
    STOP_FROM_CALLBACK,   /* Error: stop() called from within callback */
} StopResult;

/**
 * Callback signature for dispatch.
 *
 * @param user_data  Opaque pointer passed to barrier_dispatch().
 */
typedef void (*BarrierCallback)(void* user_data);

/* ============================================================================
 * Lifecycle
 * ============================================================================ */

/**
 * Initialize the barrier.
 *
 * Transitions: UNINITIALIZED/DESTROYED -> ACTIVE
 *
 * FAIL-FIRST: Aborts on mutex/cond allocation failure.
 * Idempotent: No-op if already initialized.
 */
void barrier_init(void);

/**
 * Destroy the barrier and release resources.
 *
 * Transitions: STOPPED -> DESTROYED
 *
 * Precondition: stop() must have been called (or never started).
 * Idempotent: No-op if already destroyed or never initialized.
 *
 * After destroy():
 *   - try_enter() returns false (graceful, not error)
 *   - leave() is no-op (graceful, not error)
 *   - stop() returns STOP_OK (idempotent)
 */
void barrier_destroy(void);

/* ============================================================================
 * Protected Section API
 * ============================================================================ */

/**
 * Try to enter a protected section.
 *
 * @return true if entered successfully (MUST call barrier_leave()),
 *         false if barrier not active (destroyed, stopping, or uninitialized).
 *
 * Protocol:
 *   1. Check initialized — return false if not
 *   2. Check stopping flag — return false if stopping
 *   3. Increment active count (acquire-release)
 *   4. Double-check stopping — decrement and return false if race
 *   5. Increment thread-local depth
 *   6. Return true
 *
 * Usage:
 *   if (barrier_try_enter()) {
 *       // ... protected code, barrier resources valid ...
 *       barrier_leave();
 *   }
 *
 * Graceful: Returns false for destroyed/uninitialized state (valid runtime).
 * Thread-safe: Concurrent calls OK.
 */
[[nodiscard]]
bool barrier_try_enter(void);

/**
 * Leave a protected section.
 *
 * Must be called exactly once after each successful barrier_try_enter().
 *
 * Protocol:
 *   1. Check initialized — no-op if destroyed (late leave after stop)
 *   2. FAIL-FIRST: abort if depth == 0 (mismatched enter/leave)
 *   3. Decrement thread-local depth
 *   4. Decrement active count (release)
 *   5. Signal condition if count reaches 0 during stop
 *
 * Graceful: No-op if barrier destroyed (late leave after stop is valid).
 * FAIL-FIRST: Aborts on mismatched enter/leave (programming error).
 */
void barrier_leave(void);

/**
 * Stop the barrier and wait for all in-flight callbacks.
 *
 * @return STOP_OK if stopped successfully,
 *         STOP_FROM_CALLBACK if called from within a callback.
 *
 * Protocol:
 *   1. Check thread-local depth — return STOP_FROM_CALLBACK if > 0
 *   2. Check initialized — return STOP_OK if not (idempotent)
 *   3. Lock mutex
 *   4. Check already stopping — return STOP_OK if yes (idempotent)
 *   5. Set stopping flag (release)
 *   6. Wait on condition until active count == 0
 *   7. Unlock mutex, return STOP_OK
 *
 * Thread-safe: Concurrent stop() calls serialize via mutex.
 * Idempotent: Multiple calls return STOP_OK.
 */
[[nodiscard]]
StopResult barrier_stop(void);

/* ============================================================================
 * Dispatch API (convenience wrapper)
 * ============================================================================ */

/**
 * Dispatch a callback through the barrier.
 *
 * Equivalent to:
 *   if (barrier_try_enter()) {
 *       cb(user_data);
 *       barrier_leave();
 *   }
 *
 * @param cb         Callback to execute. nullptr is no-op.
 * @param user_data  Opaque pointer passed to callback.
 *
 * Thread-safe: Concurrent calls OK.
 */
void barrier_dispatch(BarrierCallback cb, void* user_data);

/* ============================================================================
 * Query API
 * ============================================================================ */

/**
 * Check if barrier is currently stopping or stopped.
 *
 * @return true if stop() in progress or completed, false otherwise.
 *
 * Graceful: Returns false if not initialized (valid state).
 */
bool barrier_is_stopping(void);

/**
 * Get current active callback count.
 *
 * @return Number of callbacks currently in protected sections.
 *
 * Note: For testing/debugging. Value may change immediately after return.
 * Graceful: Returns 0 if not initialized.
 */
int64_t barrier_active_count(void);

/**
 * Check if current thread is inside a protected section.
 *
 * @return true if barrier_try_enter() succeeded and barrier_leave() not yet called.
 *
 * Thread-local: Per-thread state, supports nested enter/leave.
 */
bool barrier_in_callback(void);

#endif /* TRACKING_BARRIER_H */
