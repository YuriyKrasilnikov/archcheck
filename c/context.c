/**
 * Platform Context Implementation
 *
 * Provides OS/platform level context extraction.
 * Thread-safe, no global state.
 *
 * Implements:
 *   context_thread_id()    — via pthread_self()
 *   context_timestamp_ns() — via clock_gettime(CLOCK_MONOTONIC)
 *
 * Does NOT implement (Python-dependent, see _tracking.c):
 *   context_coro_id()
 *   context_task_id()
 *
 * C23: constexpr
 * POSIX: pthread_self(), clock_gettime()
 *
 * Thread Safety: All functions reentrant, no mutable state.
 */

#define _GNU_SOURCE

#include "tracking/context.h"

#include <pthread.h>
#include <time.h>

/* ============================================================================
 * Constants
 * ============================================================================ */

constexpr uint64_t NANOS_PER_SECOND = 1000000000ULL;

/* ============================================================================
 * Platform Context Implementation
 * ============================================================================ */

uint64_t context_thread_id(void) {
    return (uint64_t)pthread_self();
}

uint64_t context_timestamp_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * NANOS_PER_SECOND + (uint64_t)ts.tv_nsec;
}

/*
 * NOTE: context_coro_id() and context_task_id() are declared in context.h
 * but implemented in _tracking.c which has access to Python runtime.
 *
 * This module (context.c) provides platform-level context only.
 * Python runtime context requires PyThreadState access.
 */
