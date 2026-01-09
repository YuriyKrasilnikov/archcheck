/**
 * StringTable TSan Tests
 *
 * Standalone runner (no Criterion — incompatible with TSan).
 * TSan detects races automatically; we just exercise concurrent code paths.
 *
 * C23: constexpr, _Atomic
 * POSIX: pthread (TSan-compatible, unlike <threads.h>)
 */

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "tracking/interning.h"

/* ============================================================================
 * Configuration
 * ============================================================================ */

constexpr int NUM_THREADS = 8;
constexpr int INTERNS_PER_THREAD = 10000;
constexpr int UNIQUE_STRINGS = 1000;

/* ============================================================================
 * Synchronization
 * ============================================================================ */

static _Atomic(int) g_ready = 0;
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
 * Worker Data
 * ============================================================================ */

typedef struct {
    int thread_id;
    const char** results;
} WorkerData;

/* ============================================================================
 * Workers
 * ============================================================================ */

static void* worker_shared_strings(void* arg) {
    WorkerData* data = (WorkerData*)arg;

    /* Barrier: wait for all threads to start */
    atomic_fetch_add(&g_ready, 1);
    while (atomic_load(&g_ready) < NUM_THREADS) {
        sched_yield();
    }

    /* Intern shared strings (same set across all threads) */
    for (int i = 0; i < INTERNS_PER_THREAD; i++) {
        char buf[64];
        snprintf(buf, sizeof(buf), "shared_%d", i % UNIQUE_STRINGS);
        data->results[i] = string_intern(buf);
    }

    return NULL;
}

static void* worker_same_string(void* arg) {
    WorkerData* data = (WorkerData*)arg;

    atomic_fetch_add(&g_ready, 1);
    while (atomic_load(&g_ready) < NUM_THREADS) {
        sched_yield();
    }

    /* All threads intern THE SAME string */
    for (int i = 0; i < INTERNS_PER_THREAD; i++) {
        data->results[i] = string_intern("the_same_string");
    }

    return NULL;
}

static void* worker_unique_strings(void* arg) {
    WorkerData* data = (WorkerData*)arg;

    atomic_fetch_add(&g_ready, 1);
    while (atomic_load(&g_ready) < NUM_THREADS) {
        sched_yield();
    }

    /* Each thread interns unique strings */
    for (int i = 0; i < INTERNS_PER_THREAD; i++) {
        char buf[64];
        snprintf(buf, sizeof(buf), "thread%d_str%d", data->thread_id, i);
        data->results[i] = string_intern(buf);
    }

    return NULL;
}

/* ============================================================================
 * Tests
 * ============================================================================ */

static int test_concurrent_shared(void) {
    string_table_init(256);
    atomic_store(&g_ready, 0);

    pthread_t threads[NUM_THREADS];
    WorkerData data[NUM_THREADS];
    static const char* results[NUM_THREADS][INTERNS_PER_THREAD];

    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        data[t].results = results[t];
        if (pthread_create(&threads[t], NULL, worker_shared_strings, &data[t]) != 0) {
            return 1;
        }
    }

    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_join(threads[t], NULL);
    }

    /* Verify: same string content → same pointer across threads */
    for (int i = 0; i < UNIQUE_STRINGS; i++) {
        const char* expected = results[0][i];
        for (int t = 1; t < NUM_THREADS; t++) {
            if (results[t][i] != expected) {
                fprintf(stderr, "    Pointer mismatch: thread 0=%p, thread %d=%p\n",
                    (void*)expected, t, (void*)results[t][i]);
                string_table_destroy();
                return 1;
            }
        }
    }

    if (string_table_count() != UNIQUE_STRINGS) {
        fprintf(stderr, "    Count mismatch: expected %d, got %zu\n",
            UNIQUE_STRINGS, string_table_count());
        string_table_destroy();
        return 1;
    }

    string_table_destroy();
    return 0;
}

static int test_concurrent_same(void) {
    string_table_init(64);
    atomic_store(&g_ready, 0);

    pthread_t threads[NUM_THREADS];
    WorkerData data[NUM_THREADS];
    static const char* results[NUM_THREADS][INTERNS_PER_THREAD];

    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        data[t].results = results[t];
        pthread_create(&threads[t], NULL, worker_same_string, &data[t]);
    }

    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_join(threads[t], NULL);
    }

    /* All results must be identical pointer */
    const char* expected = results[0][0];
    for (int t = 0; t < NUM_THREADS; t++) {
        for (int i = 0; i < INTERNS_PER_THREAD; i++) {
            if (results[t][i] != expected) {
                string_table_destroy();
                return 1;
            }
        }
    }

    if (string_table_count() != 1) {
        string_table_destroy();
        return 1;
    }

    string_table_destroy();
    return 0;
}

static int test_concurrent_unique(void) {
    string_table_init(1024);
    atomic_store(&g_ready, 0);

    pthread_t threads[NUM_THREADS];
    WorkerData data[NUM_THREADS];
    static const char* results[NUM_THREADS][INTERNS_PER_THREAD];

    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        data[t].results = results[t];
        pthread_create(&threads[t], NULL, worker_unique_strings, &data[t]);
    }

    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_join(threads[t], NULL);
    }

    /* All pointers non-null */
    for (int t = 0; t < NUM_THREADS; t++) {
        for (int i = 0; i < INTERNS_PER_THREAD; i++) {
            if (results[t][i] == NULL) {
                string_table_destroy();
                return 1;
            }
        }
    }

    size_t expected_count = (size_t)NUM_THREADS * INTERNS_PER_THREAD;
    if (string_table_count() != expected_count) {
        fprintf(stderr, "    Count: expected %zu, got %zu\n",
            expected_count, string_table_count());
        string_table_destroy();
        return 1;
    }

    string_table_destroy();
    return 0;
}

static int test_pointer_stability(void) {
    string_table_init(64);

    /* Pre-intern some strings */
    constexpr int PRE_COUNT = 100;
    const char* pre_ptrs[PRE_COUNT];
    char pre_bufs[PRE_COUNT][32];

    for (int i = 0; i < PRE_COUNT; i++) {
        snprintf(pre_bufs[i], sizeof(pre_bufs[i]), "pre_%d", i);
        pre_ptrs[i] = string_intern(pre_bufs[i]);
    }

    /* Hammer with concurrent inserts */
    atomic_store(&g_ready, 0);

    pthread_t threads[NUM_THREADS];
    WorkerData data[NUM_THREADS];
    static const char* results[NUM_THREADS][INTERNS_PER_THREAD];

    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        data[t].results = results[t];
        pthread_create(&threads[t], NULL, worker_unique_strings, &data[t]);
    }

    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_join(threads[t], NULL);
    }

    /* Pre-interned pointers still valid */
    for (int i = 0; i < PRE_COUNT; i++) {
        const char* again = string_intern(pre_bufs[i]);
        if (pre_ptrs[i] != again) {
            fprintf(stderr, "    Pointer changed for '%s': %p → %p\n",
                pre_bufs[i], (void*)pre_ptrs[i], (void*)again);
            string_table_destroy();
            return 1;
        }
        if (strcmp(pre_ptrs[i], pre_bufs[i]) != 0) {
            string_table_destroy();
            return 1;
        }
    }

    string_table_destroy();
    return 0;
}

/* ============================================================================
 * Main
 * ============================================================================ */

int main(void) {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║           StringTable TSan Tests (8 threads)                 ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");

    RUN_TEST(test_concurrent_shared);
    RUN_TEST(test_concurrent_same);
    RUN_TEST(test_concurrent_unique);
    RUN_TEST(test_pointer_stability);

    printf("\n");
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("Results: %d passed, %d failed\n",
        atomic_load(&g_tests_passed), atomic_load(&g_tests_failed));
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("\n");

    return atomic_load(&g_tests_failed) > 0 ? 1 : 0;
}
