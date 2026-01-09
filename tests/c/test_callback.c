/**
 * Event Callback Tests
 *
 * Tests event dispatch through callback system.
 *
 * C23: constexpr, nullptr, _Atomic
 */

#define _GNU_SOURCE

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>

#include "tracking/callback.h"
#include "tracking/context.h"
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
 * Mock Callback State
 * ============================================================================ */

static _Atomic(int) g_callback_count = 0;
static _Atomic(EventKind) g_last_kind = EVENT_CALL;
static _Atomic(uint64_t) g_last_thread_id = 0;

static void reset_callback_state(void) {
    atomic_store(&g_callback_count, 0);
    atomic_store(&g_last_kind, EVENT_CALL);
    atomic_store(&g_last_thread_id, 0);
}

static void test_callback(const RawEvent* event, void* user_data) {
    (void)user_data;

    atomic_fetch_add(&g_callback_count, 1);
    atomic_store(&g_last_kind, event->kind);

    if (event->kind == EVENT_CALL) {
        atomic_store(&g_last_thread_id, event->data.call.thread_id);
    }
}

/* ============================================================================
 * Tests
 * ============================================================================ */

/**
 * test_start_stop: Basic lifecycle.
 */
static int test_start_stop(void) {
    reset_callback_state();

    tracking_start(test_callback, nullptr);

    if (!tracking_is_active()) {
        (void)tracking_stop();
        return 1;
    }

    StopResult result = tracking_stop();
    if (result != STOP_OK) {
        return 1;
    }

    if (tracking_is_active()) {
        return 1;
    }

    return 0;
}

/**
 * test_dispatch_call: Dispatch EVENT_CALL.
 */
static int test_dispatch_call(void) {
    reset_callback_state();
    tracking_start(test_callback, nullptr);

    RawEvent event = {
        .kind = EVENT_CALL,
        .data.call = {
            .callee_file = "test.py",
            .callee_line = 10,
            .callee_func = "main",
            .caller_file = nullptr,
            .caller_line = 0,
            .caller_func = nullptr,
            .thread_id = context_thread_id(),
            .coro_id = 0,
            .timestamp_ns = context_timestamp_ns(),
        },
    };

    tracking_dispatch(&event);

    if (atomic_load(&g_callback_count) != 1) {
        (void)tracking_stop();
        return 1;
    }

    if (atomic_load(&g_last_kind) != EVENT_CALL) {
        (void)tracking_stop();
        return 1;
    }

    (void)tracking_stop();
    return 0;
}

/**
 * test_dispatch_return: Dispatch EVENT_RETURN.
 */
static int test_dispatch_return(void) {
    reset_callback_state();
    tracking_start(test_callback, nullptr);

    RawEvent event = {
        .kind = EVENT_RETURN,
        .data.ret = {
            .file = "test.py",
            .line = 10,
            .func = "main",
            .thread_id = context_thread_id(),
            .timestamp_ns = context_timestamp_ns(),
            .has_exception = false,
        },
    };

    tracking_dispatch(&event);

    if (atomic_load(&g_callback_count) != 1) {
        (void)tracking_stop();
        return 1;
    }

    if (atomic_load(&g_last_kind) != EVENT_RETURN) {
        (void)tracking_stop();
        return 1;
    }

    (void)tracking_stop();
    return 0;
}

/**
 * test_dispatch_create: Dispatch EVENT_CREATE.
 */
static int test_dispatch_create(void) {
    reset_callback_state();
    tracking_start(test_callback, nullptr);

    RawEvent event = {
        .kind = EVENT_CREATE,
        .data.create = {
            .obj_id = 0x12345678,
            .type_name = "MyClass",
            .file = "test.py",
            .line = 20,
            .func = "factory",
            .thread_id = context_thread_id(),
            .timestamp_ns = context_timestamp_ns(),
        },
    };

    tracking_dispatch(&event);

    if (atomic_load(&g_last_kind) != EVENT_CREATE) {
        (void)tracking_stop();
        return 1;
    }

    (void)tracking_stop();
    return 0;
}

/**
 * test_dispatch_destroy: Dispatch EVENT_DESTROY.
 */
static int test_dispatch_destroy(void) {
    reset_callback_state();
    tracking_start(test_callback, nullptr);

    RawEvent event = {
        .kind = EVENT_DESTROY,
        .data.destroy = {
            .obj_id = 0x12345678,
            .type_name = "MyClass",
            .thread_id = context_thread_id(),
            .timestamp_ns = context_timestamp_ns(),
        },
    };

    tracking_dispatch(&event);

    if (atomic_load(&g_last_kind) != EVENT_DESTROY) {
        (void)tracking_stop();
        return 1;
    }

    (void)tracking_stop();
    return 0;
}

/**
 * test_null_callback_safe: Null callback is no-op.
 */
static int test_null_callback_safe(void) {
    tracking_start(nullptr, nullptr);

    RawEvent event = {
        .kind = EVENT_CALL,
        .data.call = {0},
    };

    /* Should not crash */
    tracking_dispatch(&event);
    tracking_dispatch(&event);
    tracking_dispatch(&event);

    (void)tracking_stop();
    return 0;
}

/**
 * test_dispatch_after_stop: Dispatch after stop is ignored.
 */
static int test_dispatch_after_stop(void) {
    reset_callback_state();
    tracking_start(test_callback, nullptr);

    (void)tracking_stop();

    RawEvent event = {
        .kind = EVENT_CALL,
        .data.call = {0},
    };

    tracking_dispatch(&event);

    if (atomic_load(&g_callback_count) != 0) {
        return 1;
    }

    return 0;
}

/**
 * test_multiple_dispatch: Multiple events dispatched.
 */
static int test_multiple_dispatch(void) {
    reset_callback_state();
    tracking_start(test_callback, nullptr);

    constexpr int N = 100;
    for (int i = 0; i < N; i++) {
        RawEvent event = {
            .kind = EVENT_CALL,
            .data.call = {
                .callee_line = i,
                .thread_id = context_thread_id(),
                .timestamp_ns = context_timestamp_ns(),
            },
        };
        tracking_dispatch(&event);
    }

    if (atomic_load(&g_callback_count) != N) {
        (void)tracking_stop();
        return 1;
    }

    (void)tracking_stop();
    return 0;
}

/**
 * test_user_data_passed: User data received in callback.
 */
static int g_user_data_value = 0;

static void user_data_callback(const RawEvent* event, void* user_data) {
    (void)event;
    int* ptr = (int*)user_data;
    g_user_data_value = *ptr;
}

static int test_user_data_passed(void) {
    g_user_data_value = 0;
    int expected = 42;

    tracking_start(user_data_callback, &expected);

    RawEvent event = {.kind = EVENT_CALL, .data.call = {0}};
    tracking_dispatch(&event);

    if (g_user_data_value != expected) {
        (void)tracking_stop();
        return 1;
    }

    (void)tracking_stop();
    return 0;
}

/**
 * test_thread_id_correct: Thread ID matches pthread_self.
 */
static int test_thread_id_correct(void) {
    reset_callback_state();
    tracking_start(test_callback, nullptr);

    uint64_t expected_tid = context_thread_id();

    RawEvent event = {
        .kind = EVENT_CALL,
        .data.call = {
            .thread_id = expected_tid,
        },
    };

    tracking_dispatch(&event);

    if (atomic_load(&g_last_thread_id) != expected_tid) {
        (void)tracking_stop();
        return 1;
    }

    (void)tracking_stop();
    return 0;
}

/**
 * test_timestamp_monotonic: Timestamps are monotonically increasing.
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
 * test_concurrent_dispatch: Multiple threads dispatch.
 */
constexpr int NUM_THREADS = 8;
constexpr int EVENTS_PER_THREAD = 100;
static _Atomic(int) g_ready = 0;

static void* concurrent_worker(void* arg) {
    (void)arg;

    /* Barrier */
    atomic_fetch_add(&g_ready, 1);
    while (atomic_load(&g_ready) < NUM_THREADS) {
        sched_yield();
    }

    for (int i = 0; i < EVENTS_PER_THREAD; i++) {
        RawEvent event = {
            .kind = EVENT_CALL,
            .data.call = {
                .thread_id = context_thread_id(),
                .timestamp_ns = context_timestamp_ns(),
            },
        };
        tracking_dispatch(&event);
    }

    return nullptr;
}

static int test_concurrent_dispatch(void) {
    reset_callback_state();
    atomic_store(&g_ready, 0);
    tracking_start(test_callback, nullptr);

    pthread_t threads[NUM_THREADS];
    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_create(&threads[t], nullptr, concurrent_worker, nullptr);
    }

    for (int t = 0; t < NUM_THREADS; t++) {
        pthread_join(threads[t], nullptr);
    }

    int expected = NUM_THREADS * EVENTS_PER_THREAD;
    if (atomic_load(&g_callback_count) != expected) {
        fprintf(stderr, "    Expected %d, got %d\n",
            expected, atomic_load(&g_callback_count));
        (void)tracking_stop();
        return 1;
    }

    (void)tracking_stop();
    return 0;
}

/**
 * test_stop_from_callback_detected: Stop from callback returns error.
 */
static StopResult g_stop_result = STOP_OK;

static void stop_from_callback(const RawEvent* event, void* user_data) {
    (void)event;
    (void)user_data;
    g_stop_result = tracking_stop();
}

static int test_stop_from_callback_detected(void) {
    g_stop_result = STOP_OK;
    tracking_start(stop_from_callback, nullptr);

    RawEvent event = {.kind = EVENT_CALL, .data.call = {0}};
    tracking_dispatch(&event);

    /* Stop from callback should return STOP_FROM_CALLBACK */
    if (g_stop_result != STOP_FROM_CALLBACK) {
        /* Clean up */
        (void)tracking_stop();
        return 1;
    }

    /* Normal stop should work */
    StopResult result = tracking_stop();
    if (result != STOP_OK) {
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
    printf("║           Event Callback Tests                               ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n");
    printf("\n");

    RUN_TEST(test_start_stop);
    RUN_TEST(test_dispatch_call);
    RUN_TEST(test_dispatch_return);
    RUN_TEST(test_dispatch_create);
    RUN_TEST(test_dispatch_destroy);
    RUN_TEST(test_null_callback_safe);
    RUN_TEST(test_dispatch_after_stop);
    RUN_TEST(test_multiple_dispatch);
    RUN_TEST(test_user_data_passed);
    RUN_TEST(test_thread_id_correct);
    RUN_TEST(test_timestamp_monotonic);
    RUN_TEST(test_concurrent_dispatch);
    RUN_TEST(test_stop_from_callback_detected);

    printf("\n");
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("Results: %d passed, %d failed\n",
        atomic_load(&g_tests_passed), atomic_load(&g_tests_failed));
    printf("─────────────────────────────────────────────────────────────────\n");
    printf("\n");

    return atomic_load(&g_tests_failed) > 0 ? 1 : 0;
}
