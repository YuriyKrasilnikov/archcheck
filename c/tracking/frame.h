/**
 * Frame Stack
 *
 * Thread-local call stack for tracking caller chains.
 * All strings INTERNED via StringTable.
 *
 * Contract:
 *   - StackFrame.file and .func are INTERNED (pointer stable)
 *   - Caller obtained from thread-local call stack
 *   - Stack grows dynamically — NO arbitrary limits
 *   - FAIL-FIRST: abort on allocation failure or invalid operation
 *
 * Data Completeness:
 *   Stack captures ALL frames. No truncation.
 *   Memory bounded by actual recursion depth, not arbitrary constant.
 *
 * String Ownership:
 *   - file/func: INTERNED pointers (do NOT free)
 *   - Valid until string_table_destroy()
 *
 * C23: constexpr, nullptr, [[nodiscard]]
 */

#ifndef TRACKING_FRAME_H
#define TRACKING_FRAME_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

/* ============================================================================
 * Types
 * ============================================================================ */

/**
 * Frame location information.
 *
 * All string fields are INTERNED (pointer equality valid).
 * Do NOT free file/func — owned by StringTable.
 */
typedef struct {
    const char* file;   /* Interned file path (or nullptr for builtins) */
    int32_t line;       /* First line number */
    const char* func;   /* Interned function name (qualname) */
} StackFrame;

/** Sentinel for "no caller" (top of stack). */
constexpr StackFrame FRAME_NO_CALLER = {nullptr, 0, nullptr};

/* ============================================================================
 * Call Stack API (Thread-Local)
 * ============================================================================ */

/**
 * Push frame onto thread-local call stack.
 *
 * @param info  Frame to push. Must not be nullptr.
 *
 * FAIL-FIRST: Aborts if info is nullptr or allocation fails.
 * Dynamic growth: No stack depth limit.
 */
void frame_stack_push(const StackFrame* info);

/**
 * Pop frame from thread-local call stack.
 *
 * FAIL-FIRST: Aborts if stack is empty (underflow).
 */
void frame_stack_pop(void);

/**
 * Get current caller (frame below top of stack).
 *
 * @return Pointer to caller StackFrame, or nullptr if stack depth < 2.
 *
 * Returned pointer valid until next push/pop on same thread.
 * Thread-local: no synchronization needed.
 */
[[nodiscard]]
const StackFrame* frame_stack_caller(void);

/**
 * Get current stack depth.
 *
 * @return Number of frames on stack.
 */
[[nodiscard]]
size_t frame_stack_depth(void);

/**
 * Clear thread-local call stack.
 *
 * Resets depth to 0, keeps allocation for reuse.
 * Called on thread cleanup or error recovery.
 */
void frame_stack_clear(void);

/**
 * Destroy thread-local call stack and free memory.
 *
 * Call before thread exit to prevent memory leak.
 * After destroy, push/pop will reallocate.
 */
void frame_stack_destroy(void);

/* ============================================================================
 * Utility
 * ============================================================================ */

/**
 * Check if StackFrame is empty (no location).
 *
 * @param info  Frame to check.
 * @return true if file and func are both nullptr.
 */
[[nodiscard]]
static inline bool frame_is_empty(const StackFrame* info) {
    return info == nullptr || (info->file == nullptr && info->func == nullptr);
}

/**
 * Check if two StackFrame are equal.
 *
 * Uses pointer equality (interned strings).
 *
 * @param a  First frame.
 * @param b  Second frame.
 * @return true if all fields equal.
 */
[[nodiscard]]
static inline bool frame_equals(const StackFrame* a, const StackFrame* b) {
    if (a == nullptr || b == nullptr) {
        return a == b;
    }
    return a->file == b->file && a->line == b->line && a->func == b->func;
}

#endif /* TRACKING_FRAME_H */
