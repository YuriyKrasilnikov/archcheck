#ifndef TRACKING_MEMORY_H
#define TRACKING_MEMORY_H

#include <string.h>
#include <stdlib.h>
#include "types.h"

/* ============================================================================
 * Safe string copy with guaranteed null-termination
 * ============================================================================ */

#define SAFE_STRCPY(dst, src, size) do { \
    strncpy((dst), (src), (size) - 1);   \
    (dst)[(size) - 1] = '\0';            \
} while(0)

/* ============================================================================
 * FrameInfo operations
 * ============================================================================ */

/**
 * Deep copy FrameInfo - allocates new strings.
 * dst must be zero-initialized or will leak.
 */
static inline void copy_frame_info(FrameInfo *dst, const FrameInfo *src) {
    if (!src) {
        return;
    }
    dst->file = src->file ? strdup(src->file) : nullptr;
    dst->line = src->line;
    dst->func = src->func ? strdup(src->func) : nullptr;
}

/**
 * Free FrameInfo strings.
 * Safe to call with nullptr info.
 */
static inline void free_frame_info(FrameInfo *info) {
    if (!info) {
        return;
    }
    free(info->file);
    free(info->func);
    info->file = nullptr;
    info->func = nullptr;
}

#endif /* TRACKING_MEMORY_H */
