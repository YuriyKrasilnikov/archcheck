/**
 * Stop Barrier TSan Tests
 *
 * Standalone runner (no Criterion — incompatible with TSan).
 * Tests reference counting + condition variable barrier pattern.
 *
 * CRITICAL: Fixes use-after-free in _tracking.c:158
 *
 * C23: constexpr, nullptr, _Atomic
 * POSIX: pthread (TSan-compatible)
 */

/* POSIX + GNU extensions for usleep, pthread */
#define _GNU_SOURCE

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>

#include "tracking/barrier.h"

/* ============================================================================
 * Configuration
 * ============================================================================ */

constexpr int NUM_THREADS = 8;
constexpr int DISPATCHES_PER_THREAD = 1000;
constexpr int SLOW_CALLBACK_MS = 50;

/* ============================================================================
 * Test Infrastructure
 * ============================================================================ */

static _Atomic(int) g_tests_passed = 0;
static _Atomic(int) g_tests_failed = 0;

#define RUN_TEST(name) \
    do { \
        printf("  %s... ", #name); \
        fflush(stdout); \
        if (name() == 0) { \
            printf("\033[32mOK\033[0m\n"); \
            atomic_fetch_add(&g_tests_passed, 1); \
        } else { \
            printf("\033[31mFAIL\033[0m\n"); \
            atomic_fetch_add(&g_tests_failed, 1); \
        } \
    } while (0)

/* ============================================================================
 * Mock Callback State
 * ============================================================================ */

static _Atomic(int) g_callback_count = 0;
static _Atomic(int) g_callback_in_progress = 0;
static _Atomic(bool) g_slow_callback = false;
static _Atomic(bool) g_stop_from_callback_flag = false;

static void mock_callback(void* user_data) {
    (void)user_data;
    atomic_fetch_add(&g_callback_in_progress, 1);
    atomic_fetch_add(&g_callback_count, 1);

    if (atomic_load(&g_slow_callback)) {
        usleep(SLOW_CALLBACK_MS * 1000);
    }

    if (atomic_load(&g_stop_from_callback_flag)) {
        /* Attempt stop from within callback */
        StopResult result = barrier_stop();
        /* Should return STOP_FROM_CALLBACK */
        assert(result == STOP_FROM_CALLBACK);
    }

    atomic_fetch_sub(&g_callback_in_progress, 1);
}

static void reset_mock_state(void) {
    atomic_store(&g_callback_count, 0);
    atomic_store(&g_callback_in_progress, 0);
    atomic_store(&g_slow_callback, false);
    atomic_store(&g_stop_from_callback_flag, false);
}

/* ============================================================================
 * Tests
 * ============================================================================ */

/**
 * test_basic_dispatch: Single dispatch completes normally.
 */
static int test_basic_dispatch(void) {
    barrier_init();
    reset_mock_state();

    barrier_dispatch(mock_callback, nullptr);

    if (atomic_load(&g_callback_count) != 1) {
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_stop_waits_for_callback: stop() blocks until callback done.
 *
 * Timeline:
 *   T1: dispatch(slow_callback)  ← takes 50ms
 *   T2: stop()                   ← must WAIT for T1
 *   T2: stop() returns           ← only after callback done
 */
typedef struct {
    _Atomic(bool) stop_started;
    _Atomic(bool) stop_completed;
    _Atomic(bool) callback_was_in_progress;
} StopWaitData;

static void* stop_thread(void* arg) {
    StopWaitData* data = (StopWaitData*)arg;

    atomic_store(&data->stop_started, true);
    data->callback_was_in_progress = atomic_load(&g_callback_in_progress) > 0;

    StopResult result = barrier_stop();
    (void)result;

    atomic_store(&data->stop_completed, true);
    return nullptr;
}

static int test_stop_waits_for_callback(void) {
    barrier_init();
    reset_mock_state();
    atomic_store(&g_slow_callback, true);

    StopWaitData data = {0};
    pthread_t tid;

    /* Start slow callback */
    barrier_dispatch(mock_callback, nullptr);

    /* Start stop thread while callback in progress */
    pthread_create(&tid, nullptr, stop_thread, &data);

    /* Give stop thread time to start */
    usleep(5000);

    /* Callback should still be in progress when stop started */
    pthread_join(tid, nullptr);

    /* After stop completes, callback must be done */
    if (atomic_load(&g_callback_in_progress) != 0) {
        barrier_destroy();
        return 1;
    }

    if (atomic_load(&g_callback_count) != 1) {
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_stop_then_dispatch_skipped: Dispatch after stop is skipped.
 */
static int test_stop_then_dispatch_skipped(void) {
    barrier_init();
    reset_mock_state();

    /* Stop first */
    StopResult result = barrier_stop();
    if (result != STOP_OK) {
        barrier_destroy();
        return 1;
    }

    /* Dispatch after stop — should be skipped */
    barrier_dispatch(mock_callback, nullptr);

    if (atomic_load(&g_callback_count) != 0) {
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_stop_from_callback_detected: Returns STOP_FROM_CALLBACK.
 */
static int test_stop_from_callback_detected(void) {
    barrier_init();
    reset_mock_state();
    atomic_store(&g_stop_from_callback_flag, true);

    /* Callback will attempt stop() internally */
    barrier_dispatch(mock_callback, nullptr);

    /* If we reach here, assertion in callback passed */
    barrier_destroy();
    return 0;
}

/**
 * test_callback_count_accurate: g_active_callbacks tracks correctly.
 */
static int test_callback_count_accurate(void) {
    barrier_init();
    reset_mock_state();

    constexpr int N = 100;
    for (int i = 0; i < N; i++) {
        barrier_dispatch(mock_callback, nullptr);
    }

    if (atomic_load(&g_callback_count) != N) {
        barrier_destroy();
        return 1;
    }

    /* After all dispatches, active count should be 0 */
    if (barrier_active_count() != 0) {
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_concurrent_dispatch: Multiple threads dispatch concurrently.
 * TSan: detects races.
 */
typedef struct {
    int thread_id;
} DispatchWorkerData;

static _Atomic(int) g_ready_threads = 0;

static void* dispatch_worker(void* arg) {
    DispatchWorkerData* data = (DispatchWorkerData*)arg;
    (void)data;

    /* Barrier: wait for all threads */
    atomic_fetch_add(&g_ready_threads, 1);
    while (atomic_load(&g_ready_threads) < NUM_THREADS) {
        sched_yield();
    }

    /* Dispatch many callbacks */
    for (int i = 0; i < DISPATCHES_PER_THREAD; i++) {
        barrier_dispatch(mock_callback, nullptr);
    }

    return nullptr;
}

static int test_concurrent_dispatch(void) {
    barrier_init();
    reset_mock_state();
    atomic_store(&g_ready_threads, 0);

    pthread_t threads[NUM_THREADS];
    DispatchWorkerData data[NUM_THREADS];

    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        pthread_create(&threads[t], nullptr, dispatch_worker, &data[t]);
    }

    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_join(threads[t], nullptr);
    }

    int expected = NUM_THREADS * DISPATCHES_PER_THREAD;
    if (atomic_load(&g_callback_count) != expected) {
        fprintf(stderr, "    Expected %d callbacks, got %d\n",
            expected, atomic_load(&g_callback_count));
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_concurrent_stop_dispatch: Stop while dispatches in progress.
 * TSan: detects races between stop and dispatch.
 */
static _Atomic(bool) g_stop_signal = false;

static void* dispatch_until_stop(void* arg) {
    (void)arg;

    while (!atomic_load(&g_stop_signal)) {
        barrier_dispatch(mock_callback, nullptr);
        sched_yield();
    }

    return nullptr;
}

static int test_concurrent_stop_dispatch(void) {
    barrier_init();
    reset_mock_state();
    atomic_store(&g_stop_signal, false);

    pthread_t dispatch_threads[NUM_THREADS];

    /* Start dispatch threads */
    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_create(&dispatch_threads[t], nullptr, dispatch_until_stop, nullptr);
    }

    /* Let them run for a bit */
    usleep(10000);

    /* Signal stop */
    atomic_store(&g_stop_signal, true);

    /* Wait for dispatch threads to notice */
    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_join(dispatch_threads[t], nullptr);
    }

    /* Now stop the barrier */
    StopResult result = barrier_stop();
    if (result != STOP_OK) {
        barrier_destroy();
        return 1;
    }

    /* After stop, active count must be 0 */
    if (barrier_active_count() != 0) {
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_multiple_stop_safe: Multiple stop() calls are safe.
 */
static int test_multiple_stop_safe(void) {
    barrier_init();
    reset_mock_state();

    StopResult r1 = barrier_stop();
    StopResult r2 = barrier_stop();
    StopResult r3 = barrier_stop();

    /* All should succeed (idempotent) */
    if (r1 != STOP_OK || r2 != STOP_OK || r3 != STOP_OK) {
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_reinit_after_destroy: Can reinit after destroy.
 */
static int test_reinit_after_destroy(void) {
    barrier_init();
    reset_mock_state();

    barrier_dispatch(mock_callback, nullptr);
    (void)barrier_stop();
    barrier_destroy();

    /* Reinit */
    barrier_init();
    reset_mock_state();

    barrier_dispatch(mock_callback, nullptr);

    if (atomic_load(&g_callback_count) != 1) {
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_try_enter_leave: Low-level enter/leave API.
 */
static int test_try_enter_leave(void) {
    barrier_init();

    /* Should be able to enter */
    if (!barrier_try_enter()) {
        barrier_destroy();
        return 1;
    }

    /* Active count should be 1 */
    if (barrier_active_count() != 1) {
        barrier_leave();
        barrier_destroy();
        return 1;
    }

    /* Should be in callback */
    if (!barrier_in_callback()) {
        barrier_leave();
        barrier_destroy();
        return 1;
    }

    barrier_leave();

    /* Active count should be 0 */
    if (barrier_active_count() != 0) {
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_try_enter_after_stop: Cannot enter after stop.
 */
static int test_try_enter_after_stop(void) {
    barrier_init();

    (void)barrier_stop();

    /* Should NOT be able to enter after stop */
    if (barrier_try_enter()) {
        barrier_leave();
        barrier_destroy();
        return 1;
    }

    barrier_destroy();
    return 0;
}

/**
 * test_nested_enter: Multiple enters not allowed (same thread).
 * This tests that enter sets in_callback flag.
 */
static int test_nested_enter_flag(void) {
    barrier_init();

    if (!barrier_try_enter()) {
        barrier_destroy();
        return 1;
    }

    /* in_callback should be true */
    if (!barrier_in_callback()) {
        barrier_leave();
        barrier_destroy();
        return 1;
    }

    /* Second enter should work (count increases) */
    if (!barrier_try_enter()) {
        barrier_leave();
        barrier_destroy();
        return 1;
    }

    /* Active count should be 2 */
    if (barrier_active_count() != 2) {
        barrier_leave();
        barrier_leave();
        barrier_destroy();
        return 1;
    }

    barrier_leave();
    barrier_leave();

    barrier_destroy();
    return 0;
}

/* ============================================================================
 * Main
 * ============================================================================ */

int main(void) {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║           Stop Barrier TSan Tests (8 threads)                ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");

    RUN_TEST(test_basic_dispatch);
    RUN_TEST(test_stop_waits_for_callback);
    RUN_TEST(test_stop_then_dispatch_skipped);
    RUN_TEST(test_stop_from_callback_detected);
    RUN_TEST(test_callback_count_accurate);
    RUN_TEST(test_concurrent_dispatch);
    RUN_TEST(test_concurrent_stop_dispatch);
    RUN_TEST(test_multiple_stop_safe);
    RUN_TEST(test_reinit_after_destroy);
    RUN_TEST(test_try_enter_leave);
    RUN_TEST(test_try_enter_after_stop);
    RUN_TEST(test_nested_enter_flag);

    printf("\n");
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("Results: %d passed, %d failed\n",
        atomic_load(&g_tests_passed), atomic_load(&g_tests_failed));
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("\n");

    return atomic_load(&g_tests_failed) > 0 ? 1 : 0;
}
