/**
 * StringTable Concurrency Tests (TEST-FIRST)
 *
 * Contract:
 *   - Concurrent intern() calls are thread-safe
 *   - No data races (TSan clean)
 *   - Pointer stability under concurrent access
 *   - Same string from different threads → same pointer
 *
 * C23 features: <threads.h>, _Atomic
 */

#include <criterion/criterion.h>
#include <criterion/new/assert.h>
#include <threads.h>
#include <stdatomic.h>
#include <string.h>
#include <stdio.h>

#include "tracking/interning.h"

/* ============================================================================
 * Configuration
 * ============================================================================ */

constexpr int NUM_THREADS = 8;
constexpr int INTERNS_PER_THREAD = 10000;
constexpr int UNIQUE_STRINGS = 1000;

/* ============================================================================
 * Fixtures
 * ============================================================================ */

static void setup(void) {
    string_table_init(256);
}

static void teardown(void) {
    string_table_destroy();
}

/* ============================================================================
 * Thread worker data
 * ============================================================================ */

typedef struct {
    int thread_id;
    const char** results;  /* Store interned pointers */
    _Atomic(int)* ready;   /* Barrier for synchronized start */
    _Atomic(int)* done;    /* Completion counter */
} ThreadData;

/* ============================================================================
 * Worker functions
 * ============================================================================ */

/**
 * Worker: intern many strings, some shared across threads.
 */
static int worker_intern_shared(void* arg) {
    ThreadData* data = (ThreadData*)arg;

    /* Wait for all threads ready */
    atomic_fetch_add(data->ready, 1);
    while (atomic_load(data->ready) < NUM_THREADS) {
        thrd_yield();
    }

    /* Intern strings: mix of unique and shared */
    for (int i = 0; i < INTERNS_PER_THREAD; i++) {
        char buf[64];
        /* Shared strings: same across threads (modulo UNIQUE) */
        snprintf(buf, sizeof(buf), "shared_%d", i % UNIQUE_STRINGS);
        data->results[i] = string_intern(buf);
    }

    atomic_fetch_add(data->done, 1);
    return 0;
}

/**
 * Worker: intern only unique strings per thread.
 */
static int worker_intern_unique(void* arg) {
    ThreadData* data = (ThreadData*)arg;

    /* Wait for all threads ready */
    atomic_fetch_add(data->ready, 1);
    while (atomic_load(data->ready) < NUM_THREADS) {
        thrd_yield();
    }

    /* Intern unique strings per thread */
    for (int i = 0; i < INTERNS_PER_THREAD; i++) {
        char buf[64];
        snprintf(buf, sizeof(buf), "thread%d_string%d", data->thread_id, i);
        data->results[i] = string_intern(buf);
    }

    atomic_fetch_add(data->done, 1);
    return 0;
}

/**
 * Worker: repeatedly intern same string to stress test.
 */
static int worker_intern_same(void* arg) {
    ThreadData* data = (ThreadData*)arg;

    /* Wait for all threads ready */
    atomic_fetch_add(data->ready, 1);
    while (atomic_load(data->ready) < NUM_THREADS) {
        thrd_yield();
    }

    /* All threads intern the SAME string */
    for (int i = 0; i < INTERNS_PER_THREAD; i++) {
        data->results[i] = string_intern("the_same_string");
    }

    atomic_fetch_add(data->done, 1);
    return 0;
}

/* ============================================================================
 * Tests
 * ============================================================================ */

Test(threading, concurrent_shared_strings, .init = setup, .fini = teardown) {
    /*
     * Multiple threads intern overlapping set of strings.
     * Same string from different threads must return same pointer.
     */
    thrd_t threads[NUM_THREADS];
    ThreadData data[NUM_THREADS];
    const char* results[NUM_THREADS][INTERNS_PER_THREAD];

    _Atomic(int) ready = 0;
    _Atomic(int) done = 0;

    /* Start threads */
    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        data[t].results = results[t];
        data[t].ready = &ready;
        data[t].done = &done;
        int rc = thrd_create(&threads[t], worker_intern_shared, &data[t]);
        cr_assert_eq(rc, thrd_success, "Thread %d creation failed", t);
    }

    /* Wait for completion */
    for (int t = 0; t < NUM_THREADS; t++) {
        thrd_join(threads[t], nullptr);
    }

    /* Verify: same string from different threads → same pointer */
    for (int i = 0; i < UNIQUE_STRINGS; i++) {
        const char* expected = results[0][i];
        for (int t = 1; t < NUM_THREADS; t++) {
            cr_assert_eq(results[t][i], expected,
                "String %d: thread 0 got %p, thread %d got %p",
                i, (void*)expected, t, (void*)results[t][i]);
        }
    }

    /* Verify count matches unique strings */
    size_t count = string_table_count();
    cr_assert_eq(count, UNIQUE_STRINGS,
        "Expected %d unique, got %zu", UNIQUE_STRINGS, count);
}

Test(threading, concurrent_unique_strings, .init = setup, .fini = teardown) {
    /*
     * Each thread interns completely unique strings.
     * Total count = NUM_THREADS * INTERNS_PER_THREAD.
     */
    thrd_t threads[NUM_THREADS];
    ThreadData data[NUM_THREADS];
    const char* results[NUM_THREADS][INTERNS_PER_THREAD];

    _Atomic(int) ready = 0;
    _Atomic(int) done = 0;

    /* Start threads */
    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        data[t].results = results[t];
        data[t].ready = &ready;
        data[t].done = &done;
        int rc = thrd_create(&threads[t], worker_intern_unique, &data[t]);
        cr_assert_eq(rc, thrd_success);
    }

    /* Wait for completion */
    for (int t = 0; t < NUM_THREADS; t++) {
        thrd_join(threads[t], nullptr);
    }

    /* Verify all pointers non-null */
    for (int t = 0; t < NUM_THREADS; t++) {
        for (int i = 0; i < INTERNS_PER_THREAD; i++) {
            cr_assert_not_null(results[t][i]);
        }
    }

    /* Verify count */
    size_t expected = (size_t)NUM_THREADS * INTERNS_PER_THREAD;
    size_t count = string_table_count();
    cr_assert_eq(count, expected, "Expected %zu, got %zu", expected, count);
}

Test(threading, concurrent_same_string, .init = setup, .fini = teardown) {
    /*
     * Stress test: all threads intern the SAME string repeatedly.
     * Must return same pointer, count = 1.
     */
    thrd_t threads[NUM_THREADS];
    ThreadData data[NUM_THREADS];
    const char* results[NUM_THREADS][INTERNS_PER_THREAD];

    _Atomic(int) ready = 0;
    _Atomic(int) done = 0;

    /* Start threads */
    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        data[t].results = results[t];
        data[t].ready = &ready;
        data[t].done = &done;
        int rc = thrd_create(&threads[t], worker_intern_same, &data[t]);
        cr_assert_eq(rc, thrd_success);
    }

    /* Wait for completion */
    for (int t = 0; t < NUM_THREADS; t++) {
        thrd_join(threads[t], nullptr);
    }

    /* All results must be same pointer */
    const char* expected = results[0][0];
    for (int t = 0; t < NUM_THREADS; t++) {
        for (int i = 0; i < INTERNS_PER_THREAD; i++) {
            cr_assert_eq(results[t][i], expected,
                "Thread %d iter %d: got %p, expected %p",
                t, i, (void*)results[t][i], (void*)expected);
        }
    }

    /* Only 1 unique string */
    cr_assert_eq(string_table_count(), 1);
}

Test(threading, pointer_stability_under_load, .init = setup, .fini = teardown) {
    /*
     * Pre-intern some strings, then hammer with concurrent inserts.
     * Pre-interned pointers must remain valid.
     */
    constexpr int PRE_INTERN = 100;
    const char* pre_ptrs[PRE_INTERN];
    char pre_bufs[PRE_INTERN][32];

    /* Pre-intern */
    for (int i = 0; i < PRE_INTERN; i++) {
        snprintf(pre_bufs[i], sizeof(pre_bufs[i]), "pre_%d", i);
        pre_ptrs[i] = string_intern(pre_bufs[i]);
    }

    /* Concurrent insert */
    thrd_t threads[NUM_THREADS];
    ThreadData data[NUM_THREADS];
    const char* results[NUM_THREADS][INTERNS_PER_THREAD];

    _Atomic(int) ready = 0;
    _Atomic(int) done = 0;

    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        data[t].results = results[t];
        data[t].ready = &ready;
        data[t].done = &done;
        thrd_create(&threads[t], worker_intern_unique, &data[t]);
    }

    for (int t = 0; t < NUM_THREADS; t++) {
        thrd_join(threads[t], nullptr);
    }

    /* Pre-interned pointers still valid and correct */
    for (int i = 0; i < PRE_INTERN; i++) {
        const char* again = string_intern(pre_bufs[i]);
        cr_assert_eq(pre_ptrs[i], again,
            "Pre-intern %d: pointer changed from %p to %p",
            i, (void*)pre_ptrs[i], (void*)again);
        cr_assert_str_eq(pre_ptrs[i], pre_bufs[i]);
    }
}
