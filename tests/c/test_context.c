/**
 * Context Module Tests
 *
 * Tests platform context extraction functions:
 *   - context_thread_id(): thread identifier
 *   - context_timestamp_ns(): monotonic timestamp
 *
 * Note: context_coro_id() and context_task_id() require Python runtime,
 *       tested in Python tests (test_free_threaded.py).
 *
 * C23: constexpr, nullptr, _Atomic
 * POSIX: pthread
 */

#define _GNU_SOURCE

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "tracking/context.h"

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
 * Thread ID Tests
 * ============================================================================ */

/**
 * test_thread_id_stable: Same thread returns same ID.
 */
static int test_thread_id_stable(void) {
    uint64_t id1 = context_thread_id();
    uint64_t id2 = context_thread_id();
    uint64_t id3 = context_thread_id();

    if (id1 != id2 || id2 != id3) {
        fprintf(stderr, "    Thread ID not stable: %lu, %lu, %lu\n",
            id1, id2, id3);
        return 1;
    }

    return 0;
}

/**
 * test_thread_id_nonzero: Thread ID is not zero.
 */
static int test_thread_id_nonzero(void) {
    uint64_t id = context_thread_id();

    if (id == 0) {
        fprintf(stderr, "    Thread ID is zero\n");
        return 1;
    }

    return 0;
}

/**
 * test_thread_id_distinct: Different threads have different IDs.
 */
static _Atomic(uint64_t) g_other_thread_id = 0;

static void* thread_id_worker(void* arg) {
    (void)arg;
    atomic_store(&g_other_thread_id, context_thread_id());
    return nullptr;
}

static int test_thread_id_distinct(void) {
    uint64_t main_id = context_thread_id();
    atomic_store(&g_other_thread_id, 0);

    pthread_t thread;
    pthread_create(&thread, nullptr, thread_id_worker, nullptr);
    pthread_join(thread, nullptr);

    uint64_t other_id = atomic_load(&g_other_thread_id);

    if (main_id == other_id) {
        fprintf(stderr, "    Same thread ID in different threads: %lu\n",
            main_id);
        return 1;
    }

    return 0;
}

/**
 * test_thread_id_many_threads: Each thread gets unique ID.
 */
constexpr int NUM_THREADS = 8;
static _Atomic(uint64_t) g_thread_ids[NUM_THREADS];
static _Atomic(int) g_thread_ready = 0;

static void* multi_thread_worker(void* arg) {
    int idx = *(int*)arg;

    /* Barrier: wait for all threads */
    atomic_fetch_add(&g_thread_ready, 1);
    while (atomic_load(&g_thread_ready) < NUM_THREADS) {
        sched_yield();
    }

    atomic_store(&g_thread_ids[idx], context_thread_id());
    return nullptr;
}

static int test_thread_id_many_threads(void) {
    atomic_store(&g_thread_ready, 0);
    for (int i = 0; i < NUM_THREADS; i++) {
        atomic_store(&g_thread_ids[i], 0);
    }

    pthread_t threads[NUM_THREADS];
    int indices[NUM_THREADS];

    for (int i = 0; i < NUM_THREADS; i++) {
        indices[i] = i;
        pthread_create(&threads[i], nullptr, multi_thread_worker, &indices[i]);
    }

    for (int i = 0; i < NUM_THREADS; i++) {
        pthread_join(threads[i], nullptr);
    }

    /* Check all IDs are unique */
    for (int i = 0; i < NUM_THREADS; i++) {
        for (int j = i + 1; j < NUM_THREADS; j++) {
            uint64_t id_i = atomic_load(&g_thread_ids[i]);
            uint64_t id_j = atomic_load(&g_thread_ids[j]);
            if (id_i == id_j) {
                fprintf(stderr, "    Thread %d and %d have same ID: %lu\n",
                    i, j, id_i);
                return 1;
            }
        }
    }

    return 0;
}

/* ============================================================================
 * Timestamp Tests
 * ============================================================================ */

/**
 * test_timestamp_nonzero: Timestamp is not zero.
 */
static int test_timestamp_nonzero(void) {
    uint64_t ts = context_timestamp_ns();

    if (ts == 0) {
        fprintf(stderr, "    Timestamp is zero\n");
        return 1;
    }

    return 0;
}

/**
 * test_timestamp_monotonic: Timestamps are strictly increasing.
 */
static int test_timestamp_monotonic(void) {
    uint64_t t1 = context_timestamp_ns();
    usleep(1000);  /* 1ms */
    uint64_t t2 = context_timestamp_ns();

    if (t2 <= t1) {
        fprintf(stderr, "    Timestamps not monotonic: %lu <= %lu\n", t2, t1);
        return 1;
    }

    return 0;
}

/**
 * test_timestamp_resolution: Resolution is at least millisecond.
 */
static int test_timestamp_resolution(void) {
    uint64_t t1 = context_timestamp_ns();
    usleep(1000);  /* 1ms = 1,000,000ns */
    uint64_t t2 = context_timestamp_ns();

    uint64_t delta = t2 - t1;

    /* Should be at least 500,000ns (0.5ms) to account for timing variance */
    if (delta < 500000) {
        fprintf(stderr, "    Resolution too low: delta=%lu ns\n", delta);
        return 1;
    }

    return 0;
}

/**
 * test_timestamp_rapid_calls: Rapid calls still produce increasing values.
 */
static int test_timestamp_rapid_calls(void) {
    constexpr int N = 1000;
    uint64_t prev = context_timestamp_ns();

    for (int i = 0; i < N; i++) {
        uint64_t curr = context_timestamp_ns();
        if (curr < prev) {
            fprintf(stderr, "    Non-monotonic at iteration %d: %lu < %lu\n",
                i, curr, prev);
            return 1;
        }
        prev = curr;
    }

    return 0;
}

/**
 * test_timestamp_cross_thread: Timestamps comparable across threads.
 */
static _Atomic(uint64_t) g_other_timestamp = 0;

static void* timestamp_worker(void* arg) {
    (void)arg;
    usleep(500);  /* Small delay */
    atomic_store(&g_other_timestamp, context_timestamp_ns());
    return nullptr;
}

static int test_timestamp_cross_thread(void) {
    uint64_t t1 = context_timestamp_ns();
    atomic_store(&g_other_timestamp, 0);

    pthread_t thread;
    pthread_create(&thread, nullptr, timestamp_worker, nullptr);
    pthread_join(thread, nullptr);

    uint64_t t2 = atomic_load(&g_other_timestamp);
    uint64_t t3 = context_timestamp_ns();

    /* t1 < t2 < t3 (with some tolerance for scheduling) */
    if (t2 <= t1 || t3 <= t2) {
        /* Note: This can fail under extreme scheduling conditions */
        fprintf(stderr, "    Cross-thread ordering: t1=%lu, t2=%lu, t3=%lu\n",
            t1, t2, t3);
        return 1;
    }

    return 0;
}

/* ============================================================================
 * Main
 * ============================================================================ */

int main(void) {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║           Context Module Tests                               ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");

    printf("Thread ID:\n");
    RUN_TEST(test_thread_id_stable);
    RUN_TEST(test_thread_id_nonzero);
    RUN_TEST(test_thread_id_distinct);
    RUN_TEST(test_thread_id_many_threads);

    printf("\nTimestamp:\n");
    RUN_TEST(test_timestamp_nonzero);
    RUN_TEST(test_timestamp_monotonic);
    RUN_TEST(test_timestamp_resolution);
    RUN_TEST(test_timestamp_rapid_calls);
    RUN_TEST(test_timestamp_cross_thread);

    printf("\n");
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("Results: %d passed, %d failed\n",
        atomic_load(&g_tests_passed), atomic_load(&g_tests_failed));
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("\n");

    return atomic_load(&g_tests_failed) > 0 ? 1 : 0;
}
