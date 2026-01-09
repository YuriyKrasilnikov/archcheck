/**
 * String Interning (StringTable)
 *
 * Contract:
 *   - intern(s) returns SAME pointer for SAME content (idempotent)
 *   - intern(nullptr) returns nullptr
 *   - Pointers remain valid after resize (pointer stability)
 *   - Thread-safe for concurrent intern() calls
 *
 * Architecture:
 *   strings[] — stores char* (strdup), grows but NEVER moves existing entries
 *   buckets[] — hash table of indices into strings[], rebuilt on resize
 *
 * Complexity:
 *   intern: O(1) amortized
 *   lookup: O(1)
 *
 * C23 features: constexpr, nullptr, [[nodiscard]], _Atomic
 */

#ifndef TRACKING_INTERNING_H
#define TRACKING_INTERNING_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdatomic.h>
/* Note: uses pthread internally (TSan-compatible), not <threads.h> */

/* ============================================================================
 * Constants
 * ============================================================================ */

/** Initial hash table capacity. Power of 2 for fast modulo. */
constexpr size_t STRING_TABLE_INITIAL_CAPACITY = 1024;

/** Load factor threshold for resize. At 75%, resize. */
constexpr double STRING_TABLE_LOAD_FACTOR = 0.75;

/** Tombstone marker for deleted entries (not used, but reserved). */
constexpr size_t STRING_TABLE_TOMBSTONE = SIZE_MAX;

/** Empty bucket marker. */
constexpr size_t STRING_TABLE_EMPTY = SIZE_MAX - 1;

/* ============================================================================
 * API
 * ============================================================================ */

/**
 * Initialize the global string table.
 *
 * @param initial_capacity  Initial bucket count. 0 = use default.
 *
 * FAIL-FIRST: Aborts on allocation failure.
 * Idempotent: Safe to call multiple times (no-op if initialized).
 */
void string_table_init(size_t initial_capacity);

/**
 * Destroy the global string table and free all memory.
 *
 * Idempotent: Safe to call multiple times (no-op if not initialized).
 * After destroy: intern() will abort (REQUIRE fails).
 */
void string_table_destroy(void);

/**
 * Intern a string.
 *
 * @param s  String to intern. May be nullptr.
 * @return   Interned pointer (same for same content), or nullptr if s=nullptr.
 *
 * Guarantees:
 *   - Pointer equality: intern("foo") == intern("foo")
 *   - Pointer stability: returned pointer valid until destroy()
 *   - Thread-safe: concurrent calls OK
 *
 * FAIL-FIRST: Aborts if table not initialized or allocation fails.
 */
[[nodiscard]]
const char* string_intern(const char* s);

/**
 * Get current count of interned strings.
 *
 * @return Number of unique strings in table.
 */
size_t string_table_count(void);

/**
 * Check if string table is initialized.
 *
 * @return true if init() called and destroy() not called.
 */
bool string_table_is_initialized(void);

/* ============================================================================
 * Design for Known Future (Phase 5: Succinct)
 * ============================================================================ */

/**
 * Lookup string by index.
 *
 * @param idx  Index (0 <= idx < string_table_count()).
 * @return     String at index.
 *
 * FAIL-FIRST: Aborts if table not initialized or index out of bounds.
 *
 * Phase 5: Will switch to succinct trie internally.
 * Current: Direct array access.
 */
[[nodiscard]]
const char* string_table_lookup(size_t idx);

#endif /* TRACKING_INTERNING_H */
