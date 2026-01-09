/**
 * String Interning Implementation
 *
 * Architecture for Pointer Stability:
 *
 *   strings[]  — array of char*, grows via realloc
 *                existing pointers NEVER invalidated
 *                strings[i] = strdup(input)
 *
 *   buckets[]  — hash table of indices into strings[]
 *                rebuilt on resize (rehash)
 *                buckets[hash % cap] = index or EMPTY
 *
 * Thread Safety:
 *   - pthread_mutex_t protects all operations
 *   - TSan-compatible (threads.h mtx_t is NOT TSan-compatible)
 *
 * C23 features: constexpr, nullptr, _Atomic
 * POSIX: pthread_mutex_t (TSan-compatible)
 */

#include "tracking/interning.h"
#include "tracking/invariants.h"

#include <string.h>
#include <stdlib.h>
#include <pthread.h>

/* ============================================================================
 * Hash Function: FNV-1a (fast, good distribution)
 * ============================================================================ */

static inline uint64_t fnv1a_hash(const char* s) {
    constexpr uint64_t FNV_OFFSET = 14695981039346656037ULL;
    constexpr uint64_t FNV_PRIME = 1099511628211ULL;

    uint64_t hash = FNV_OFFSET;
    while (*s != '\0') {
        hash ^= (uint8_t)*s++;
        hash *= FNV_PRIME;
    }
    return hash;
}

/* ============================================================================
 * Global State
 * ============================================================================ */

typedef struct {
    /* String storage — grows, but existing pointers stable */
    char** strings;
    size_t strings_count;
    size_t strings_capacity;

    /* Hash table — indices into strings[], rebuilt on resize */
    size_t* buckets;
    size_t buckets_capacity;

    /* Thread safety (pthread for TSan compatibility) */
    pthread_mutex_t mutex;
    bool initialized;
} StringTable;

static StringTable g_table = {0};

/* ============================================================================
 * Internal: Bucket Operations
 * ============================================================================ */

/**
 * Find bucket index for string. Returns bucket containing string or empty bucket.
 *
 * @param s         String to find (must not be nullptr)
 * @param hash      Pre-computed hash of s
 * @param found     Output: true if string found, false if empty bucket
 * @return          Bucket index
 */
static size_t find_bucket(const char* s, uint64_t hash, bool* found) {
    size_t idx = hash % g_table.buckets_capacity;
    size_t start = idx;

    do {
        size_t entry = g_table.buckets[idx];

        if (entry == STRING_TABLE_EMPTY) {
            *found = false;
            return idx;
        }

        /* Compare string content */
        if (strcmp(g_table.strings[entry], s) == 0) {
            *found = true;
            return idx;
        }

        /* Linear probing */
        idx = (idx + 1) % g_table.buckets_capacity;
    } while (idx != start);

    /* Table full — should never happen due to load factor check */
    UNREACHABLE("hash table full");
}

/**
 * Resize hash table (rebuild buckets, NOT strings).
 * Called when load factor exceeded.
 */
static void resize_buckets(void) {
    size_t old_capacity = g_table.buckets_capacity;
    size_t new_capacity = old_capacity * 2;

    /* Allocate new buckets */
    size_t* new_buckets = malloc(new_capacity * sizeof(size_t));
    REQUIRE(new_buckets != nullptr, "bucket allocation failed");

    /* Initialize all to EMPTY */
    for (size_t i = 0; i < new_capacity; i++) {
        new_buckets[i] = STRING_TABLE_EMPTY;
    }

    /* Rehash all strings into new buckets */
    size_t* old_buckets = g_table.buckets;
    g_table.buckets = new_buckets;
    g_table.buckets_capacity = new_capacity;

    for (size_t i = 0; i < old_capacity; i++) {
        size_t entry = old_buckets[i];
        if (entry != STRING_TABLE_EMPTY) {
            const char* s = g_table.strings[entry];
            uint64_t hash = fnv1a_hash(s);
            bool found;
            size_t bucket = find_bucket(s, hash, &found);
            /* Must not find (we're rehashing), just insert */
            g_table.buckets[bucket] = entry;
        }
    }

    free(old_buckets);
}

/**
 * Grow strings array if needed.
 */
static void ensure_strings_capacity(void) {
    if (g_table.strings_count < g_table.strings_capacity) {
        return;
    }

    size_t new_capacity = g_table.strings_capacity * 2;
    if (new_capacity == 0) {
        new_capacity = 256;
    }

    char** new_strings = realloc(g_table.strings, new_capacity * sizeof(char*));
    REQUIRE(new_strings != nullptr, "strings array allocation failed");

    g_table.strings = new_strings;
    g_table.strings_capacity = new_capacity;
}

/* ============================================================================
 * Public API
 * ============================================================================ */

void string_table_init(size_t initial_capacity) {
    /* Idempotent: no-op if already initialized */
    if (g_table.initialized) {
        return;
    }

    /* Use default if 0 */
    if (initial_capacity == 0) {
        initial_capacity = STRING_TABLE_INITIAL_CAPACITY;
    }

    /* Round up to power of 2 */
    size_t capacity = 1;
    while (capacity < initial_capacity) {
        capacity *= 2;
    }

    /* Allocate buckets */
    g_table.buckets = malloc(capacity * sizeof(size_t));
    REQUIRE(g_table.buckets != nullptr, "bucket allocation failed");

    for (size_t i = 0; i < capacity; i++) {
        g_table.buckets[i] = STRING_TABLE_EMPTY;
    }
    g_table.buckets_capacity = capacity;

    /* Allocate strings array */
    g_table.strings_capacity = 256;
    g_table.strings = malloc(g_table.strings_capacity * sizeof(char*));
    REQUIRE(g_table.strings != nullptr, "strings array allocation failed");
    g_table.strings_count = 0;

    /* Initialize mutex (pthread for TSan compatibility) */
    int result = pthread_mutex_init(&g_table.mutex, NULL);
    REQUIRE(result == 0, "mutex init failed");

    g_table.initialized = true;
}

void string_table_destroy(void) {
    /* Idempotent: no-op if not initialized */
    if (!g_table.initialized) {
        return;
    }

    /* Free all interned strings */
    for (size_t i = 0; i < g_table.strings_count; i++) {
        free(g_table.strings[i]);
    }

    free(g_table.strings);
    free(g_table.buckets);
    pthread_mutex_destroy(&g_table.mutex);

    /* Reset state */
    g_table.strings = nullptr;
    g_table.strings_count = 0;
    g_table.strings_capacity = 0;
    g_table.buckets = nullptr;
    g_table.buckets_capacity = 0;
    g_table.initialized = false;
}

const char* string_intern(const char* s) {
    /* nullptr → nullptr */
    if (s == nullptr) {
        return nullptr;
    }

    ASSERT_INITIALIZED(g_table.initialized, "StringTable");

    uint64_t hash = fnv1a_hash(s);

    /* Lock for ALL operations (TSan-safe, no lock-free fast path) */
    pthread_mutex_lock(&g_table.mutex);

    bool found;
    size_t bucket = find_bucket(s, hash, &found);
    if (found) {
        const char* result = g_table.strings[g_table.buckets[bucket]];
        pthread_mutex_unlock(&g_table.mutex);
        return result;
    }

    /* Check load factor before insert */
    double load = (double)(g_table.strings_count + 1) / (double)g_table.buckets_capacity;
    if (load > STRING_TABLE_LOAD_FACTOR) {
        resize_buckets();
        /* Re-find bucket after resize */
        bucket = find_bucket(s, hash, &found);
        /* Must not find after resize */
        REQUIRE(!found, "string appeared during resize");
    }

    /* Ensure strings array has space */
    ensure_strings_capacity();

    /* Copy string */
    char* copy = strdup(s);
    REQUIRE(copy != nullptr, "strdup failed");

    /* Add to strings array */
    size_t string_idx = g_table.strings_count;
    g_table.strings[string_idx] = copy;
    g_table.strings_count++;

    /* Add to hash table */
    g_table.buckets[bucket] = string_idx;

    pthread_mutex_unlock(&g_table.mutex);

    ENSURE(copy != nullptr, "intern must return non-null for non-null input");
    return copy;
}

size_t string_table_count(void) {
    return g_table.strings_count;
}

bool string_table_is_initialized(void) {
    return g_table.initialized;
}

const char* string_table_lookup(size_t idx) {
    REQUIRE(g_table.initialized, "string_table_lookup: table not initialized");
    REQUIRE(idx < g_table.strings_count, "string_table_lookup: index out of bounds");

    return g_table.strings[idx];
}
