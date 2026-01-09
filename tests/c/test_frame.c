/**
 * Frame Stack Tests
 *
 * Tests thread-local call stack with dynamic growth.
 * Frame extraction from Python tested in integration tests.
 *
 * C23: constexpr, nullptr
 * FAIL-FIRST: push(nullptr) and pop(empty) abort — not tested here
 */

#define _GNU_SOURCE

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "tracking/frame.h"
#include "tracking/interning.h"

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
 * Helper: Create StackFrame with interned strings
 * ============================================================================ */

static StackFrame make_frame(const char* file, int32_t line, const char* func) {
    return (StackFrame){
        .file = file ? string_intern(file) : nullptr,
        .line = line,
        .func = func ? string_intern(func) : nullptr,
    };
}

/* ============================================================================
 * Tests
 * ============================================================================ */

/**
 * test_stack_empty: Fresh stack is empty.
 */
static int test_stack_empty(void) {
    string_table_init(64);
    frame_stack_clear();

    if (frame_stack_depth() != 0) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    if (frame_stack_caller() != nullptr) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    frame_stack_destroy();
    string_table_destroy();
    return 0;
}

/**
 * test_push_pop_single: Push/pop single frame.
 */
static int test_push_pop_single(void) {
    string_table_init(64);
    frame_stack_clear();

    StackFrame f1 = make_frame("test.py", 10, "main");
    frame_stack_push(&f1);

    if (frame_stack_depth() != 1) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    /* No caller when depth == 1 */
    if (frame_stack_caller() != nullptr) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    frame_stack_pop();

    if (frame_stack_depth() != 0) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    frame_stack_destroy();
    string_table_destroy();
    return 0;
}

/**
 * test_caller_chain: Push multiple, verify caller.
 */
static int test_caller_chain(void) {
    string_table_init(64);
    frame_stack_clear();

    StackFrame f1 = make_frame("a.py", 1, "func_a");
    StackFrame f2 = make_frame("b.py", 2, "func_b");
    StackFrame f3 = make_frame("c.py", 3, "func_c");

    frame_stack_push(&f1);
    frame_stack_push(&f2);
    frame_stack_push(&f3);

    if (frame_stack_depth() != 3) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    /* Caller of f3 should be f2 */
    const StackFrame* caller = frame_stack_caller();
    if (caller == nullptr) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    if (!frame_equals(caller, &f2)) {
        fprintf(stderr, "    Caller mismatch: expected func_b, got %s\n",
            caller->func ? caller->func : "(null)");
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    /* Pop f3, caller of f2 should be f1 */
    frame_stack_pop();
    caller = frame_stack_caller();
    if (caller == nullptr || !frame_equals(caller, &f1)) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    frame_stack_pop();
    frame_stack_pop();
    frame_stack_destroy();
    string_table_destroy();
    return 0;
}

/**
 * test_frame_equals: Pointer equality for interned strings.
 */
static int test_frame_equals(void) {
    string_table_init(64);

    StackFrame f1 = make_frame("test.py", 10, "foo");
    StackFrame f2 = make_frame("test.py", 10, "foo");
    StackFrame f3 = make_frame("test.py", 10, "bar");
    StackFrame f4 = make_frame("other.py", 10, "foo");

    /* Same content = equal (interned pointers) */
    if (!frame_equals(&f1, &f2)) {
        string_table_destroy();
        return 1;
    }

    /* Different func = not equal */
    if (frame_equals(&f1, &f3)) {
        string_table_destroy();
        return 1;
    }

    /* Different file = not equal */
    if (frame_equals(&f1, &f4)) {
        string_table_destroy();
        return 1;
    }

    string_table_destroy();
    return 0;
}

/**
 * test_frame_is_empty: Check empty detection.
 */
static int test_frame_is_empty(void) {
    StackFrame empty = FRAME_NO_CALLER;
    StackFrame partial = {.file = nullptr, .line = 0, .func = nullptr};

    if (!frame_is_empty(&empty)) {
        return 1;
    }

    if (!frame_is_empty(&partial)) {
        return 1;
    }

    if (!frame_is_empty(nullptr)) {
        return 1;
    }

    return 0;
}

/**
 * test_clear: Clear resets depth but keeps allocation.
 */
static int test_clear(void) {
    string_table_init(64);
    frame_stack_clear();

    StackFrame f = make_frame("test.py", 1, "main");
    frame_stack_push(&f);
    frame_stack_push(&f);
    frame_stack_push(&f);

    if (frame_stack_depth() != 3) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    frame_stack_clear();

    if (frame_stack_depth() != 0) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    frame_stack_destroy();
    string_table_destroy();
    return 0;
}

/**
 * test_deep_stack: Push many frames — no limit, dynamic growth.
 */
static int test_deep_stack(void) {
    string_table_init(256);
    frame_stack_clear();

    /* Push 1000 frames — should work without limit */
    constexpr int DEPTH = 1000;
    char buf[64];

    for (int i = 0; i < DEPTH; i++) {
        snprintf(buf, sizeof(buf), "func_%d", i);
        StackFrame f = make_frame("deep.py", i, buf);
        frame_stack_push(&f);
    }

    if (frame_stack_depth() != DEPTH) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    /* Verify caller chain */
    const StackFrame* caller = frame_stack_caller();
    if (caller == nullptr || caller->line != DEPTH - 2) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    /* Pop all */
    for (int i = 0; i < DEPTH; i++) {
        frame_stack_pop();
    }

    if (frame_stack_depth() != 0) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    frame_stack_destroy();
    string_table_destroy();
    return 0;
}

/**
 * test_very_deep_stack: Push 10000 frames — proves no arbitrary limit.
 */
static int test_very_deep_stack(void) {
    string_table_init(1024);
    frame_stack_clear();

    /* Push 10000 frames — well beyond typical limits */
    constexpr int DEPTH = 10000;

    for (int i = 0; i < DEPTH; i++) {
        char buf[64];
        snprintf(buf, sizeof(buf), "func_%d", i);
        StackFrame f = make_frame("very_deep.py", i, buf);
        frame_stack_push(&f);
    }

    if (frame_stack_depth() != DEPTH) {
        fprintf(stderr, "    Expected depth %d, got %zu\n", DEPTH, frame_stack_depth());
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    /* Clear instead of popping all */
    frame_stack_clear();
    frame_stack_destroy();
    string_table_destroy();
    return 0;
}

/**
 * test_destroy_and_reuse: After destroy, can push again.
 */
static int test_destroy_and_reuse(void) {
    string_table_init(64);
    frame_stack_clear();

    StackFrame f = make_frame("test.py", 1, "main");
    frame_stack_push(&f);
    frame_stack_destroy();

    /* Should be able to push again after destroy */
    frame_stack_push(&f);

    if (frame_stack_depth() != 1) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    frame_stack_destroy();
    string_table_destroy();
    return 0;
}

/**
 * test_thread_local_isolation: Each thread has own stack.
 */
constexpr int NUM_THREADS = 4;
static _Atomic(int) g_ready = 0;

typedef struct {
    int thread_id;
    int success;
} ThreadData;

static void* thread_worker(void* arg) {
    ThreadData* data = (ThreadData*)arg;

    /* Barrier: wait for all threads */
    atomic_fetch_add(&g_ready, 1);
    while (atomic_load(&g_ready) < NUM_THREADS) {
        sched_yield();
    }

    /* Each thread pushes its own frames */
    char buf[64];
    for (int i = 0; i < 10; i++) {
        snprintf(buf, sizeof(buf), "thread%d_func%d", data->thread_id, i);
        StackFrame f = make_frame("thread.py", data->thread_id * 100 + i, buf);
        frame_stack_push(&f);
    }

    /* Verify depth is 10 (not affected by other threads) */
    if (frame_stack_depth() != 10) {
        data->success = 0;
        frame_stack_destroy();
        return nullptr;
    }

    /* Clear own stack */
    frame_stack_clear();
    frame_stack_destroy();
    data->success = 1;
    return nullptr;
}

static int test_thread_local_isolation(void) {
    string_table_init(256);
    frame_stack_clear();
    atomic_store(&g_ready, 0);

    pthread_t threads[NUM_THREADS];
    ThreadData data[NUM_THREADS];

    for (int t = 0; t < NUM_THREADS; t++) {
        data[t].thread_id = t;
        data[t].success = 0;
        pthread_create(&threads[t], nullptr, thread_worker, &data[t]);
    }

    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_join(threads[t], nullptr);
    }

    /* Verify all threads succeeded */
    for (int t = 0; t < NUM_THREADS; t++) {
        if (!data[t].success) {
            fprintf(stderr, "    Thread %d failed\n", t);
            frame_stack_destroy();
            string_table_destroy();
            return 1;
        }
    }

    /* Main thread stack should be unaffected */
    if (frame_stack_depth() != 0) {
        frame_stack_destroy();
        string_table_destroy();
        return 1;
    }

    frame_stack_destroy();
    string_table_destroy();
    return 0;
}

/* ============================================================================
 * Main
 * ============================================================================ */

int main(void) {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║           Frame Stack Tests (Dynamic Growth)                 ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");

    RUN_TEST(test_stack_empty);
    RUN_TEST(test_push_pop_single);
    RUN_TEST(test_caller_chain);
    RUN_TEST(test_frame_equals);
    RUN_TEST(test_frame_is_empty);
    RUN_TEST(test_clear);
    RUN_TEST(test_deep_stack);
    RUN_TEST(test_very_deep_stack);
    RUN_TEST(test_destroy_and_reuse);
    RUN_TEST(test_thread_local_isolation);

    printf("\n");
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("Results: %d passed, %d failed\n",
        atomic_load(&g_tests_passed), atomic_load(&g_tests_failed));
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("\n");

    return atomic_load(&g_tests_failed) > 0 ? 1 : 0;
}
