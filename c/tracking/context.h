/**
 * Execution Context Module
 *
 * Provides context information for event tracking:
 *   - thread_id:    OS thread identifier
 *   - timestamp_ns: monotonic clock timestamp
 *   - coro_id:      Python coroutine identifier (Python-dependent)
 *   - task_id:      asyncio task identifier (Phase 5 stub)
 *
 * Architecture:
 *   Platform context (thread_id, timestamp_ns): standalone C, context.c
 *   Python context (coro_id, task_id): requires Python.h, in _tracking.c
 *
 * Thread Safety:
 *   All functions are thread-safe and reentrant.
 *   No global mutable state.
 *
 * C23: constexpr, nullptr, [[nodiscard]]
 * POSIX: pthread_self(), clock_gettime()
 */

#ifndef TRACKING_CONTEXT_H
#define TRACKING_CONTEXT_H

#include <stdint.h>

/* ============================================================================
 * Platform Context (standalone C)
 * ============================================================================ */

/**
 * Get current thread identifier.
 *
 * Returns platform thread ID using pthread_self().
 * Stable: same thread → same ID within process lifetime.
 * Distinct: different threads → different IDs.
 *
 * @return Thread identifier as uint64_t.
 */
[[nodiscard]]
uint64_t context_thread_id(void);

/**
 * Get current timestamp in nanoseconds.
 *
 * Uses CLOCK_MONOTONIC for consistent time ordering.
 * Monotonic: t2 > t1 guaranteed for sequential calls.
 * Resolution: nanosecond (actual precision platform-dependent).
 *
 * @return Monotonic timestamp in nanoseconds.
 */
[[nodiscard]]
uint64_t context_timestamp_ns(void);

/* ============================================================================
 * Python Runtime Context (requires Python.h)
 *
 * These functions extract context from Python runtime state.
 * Declared here for API completeness, implemented in _tracking.c.
 * ============================================================================ */

/**
 * Get current coroutine identifier.
 *
 * Extracts coroutine ID from PyThreadState current frame.
 * Returns object ID of the coroutine if inside async context.
 *
 * @return Coroutine ID, or 0 if not in async context.
 *
 * Implementation: _tracking.c (requires Python.h)
 */
[[nodiscard]]
uint64_t context_coro_id(void);

/**
 * Get current asyncio task identifier.
 *
 * Phase 5 stub. Currently returns 0.
 * Full implementation requires asyncio.current_task() call.
 *
 * @return Task ID, or 0 (stub).
 *
 * Implementation: _tracking.c (requires Python.h)
 */
[[nodiscard]]
uint64_t context_task_id(void);

#endif /* TRACKING_CONTEXT_H */
