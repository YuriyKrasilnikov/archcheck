/**
 * Frame Stack Implementation
 *
 * Thread-local call stack for tracking caller chains.
 * DYNAMIC GROWTH — no arbitrary limits.
 *
 * Architecture:
 *   tl_stack      — dynamic array (realloc on growth)
 *   tl_depth      — current stack depth (0 = empty)
 *   tl_capacity   — current allocation size
 *
 * String Ownership:
 *   StackFrame.file and .func are INTERNED pointers.
 *   Do NOT free — owned by StringTable.
 *
 * Data Completeness:
 *   Stack grows without limit. Memory bounded by actual recursion depth.
 *   Grammar compression (L3) handles memory efficiency, not truncation.
 *
 * C23: constexpr, nullptr
 * FAIL-FIRST: abort on allocation failure, never lose data
 */

#include "tracking/frame.h"
#include "tracking/invariants.h"

#include <stdlib.h>
#include <string.h>

/* ============================================================================
 * Constants
 * ============================================================================ */

/** Initial stack capacity. Grows as needed. */
constexpr size_t FRAME_STACK_INITIAL_CAPACITY = 64;

/** Growth factor when resizing. */
constexpr size_t FRAME_STACK_GROWTH_FACTOR = 2;

/* ============================================================================
 * Thread-Local State
 * ============================================================================ */

static _Thread_local StackFrame* tl_stack = nullptr;
static _Thread_local size_t tl_depth = 0;
static _Thread_local size_t tl_capacity = 0;

/* ============================================================================
 * Internal: Ensure Capacity
 * ============================================================================ */

/**
 * Ensure stack has capacity for at least one more element.
 * Grows dynamically via realloc. FAIL-FIRST on allocation failure.
 */
static void ensure_capacity(void) {
    if (tl_depth < tl_capacity) {
        return;
    }

    size_t new_capacity = tl_capacity == 0
        ? FRAME_STACK_INITIAL_CAPACITY
        : tl_capacity * FRAME_STACK_GROWTH_FACTOR;

    StackFrame* new_stack = realloc(tl_stack, new_capacity * sizeof(StackFrame));
    REQUIRE(new_stack != nullptr, "frame stack allocation failed");

    tl_stack = new_stack;
    tl_capacity = new_capacity;
}

/* ============================================================================
 * Call Stack API
 * ============================================================================ */

void frame_stack_push(const StackFrame* info) {
    REQUIRE(info != nullptr, "frame_stack_push: info must not be null");

    ensure_capacity();

    /* Shallow copy (strings are interned, just copy pointers) */
    tl_stack[tl_depth] = *info;
    tl_depth++;
}

void frame_stack_pop(void) {
    REQUIRE(tl_depth > 0, "frame_stack_pop: stack underflow");

    tl_depth--;
    /* Clear popped entry for safety */
    tl_stack[tl_depth] = FRAME_NO_CALLER;
}

const StackFrame* frame_stack_caller(void) {
    /* Caller is one below top of stack */
    if (tl_depth < 2) {
        return nullptr;  /* No caller available — valid state, not error */
    }
    return &tl_stack[tl_depth - 2];
}

size_t frame_stack_depth(void) {
    return tl_depth;
}

void frame_stack_clear(void) {
    tl_depth = 0;
    /* Keep allocation for reuse */
}

void frame_stack_destroy(void) {
    free(tl_stack);
    tl_stack = nullptr;
    tl_depth = 0;
    tl_capacity = 0;
}
