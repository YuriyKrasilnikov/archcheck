/**
 * StringTable Tests (TEST-FIRST)
 *
 * Contract:
 *   - intern(s) returns same pointer for same content (idempotent)
 *   - intern(nullptr) returns nullptr
 *   - intern("") valid (empty string)
 *   - pointers remain valid after resize
 *   - thread-safe (see test_threading.c)
 *
 * C23 features: constexpr, nullptr
 */

#include <criterion/criterion.h>
#include <criterion/new/assert.h>
#include <string.h>
#include <stdio.h>

/* Header under test (will be created) */
#include "tracking/interning.h"

/* ============================================================================
 * Fixtures
 * ============================================================================ */

static void setup(void) {
    string_table_init(64);  /* Small capacity to test resize */
}

static void teardown(void) {
    string_table_destroy();
}

/* ============================================================================
 * Basic invariants
 * ============================================================================ */

Test(interning, idempotent, .init = setup, .fini = teardown) {
    /* SAME string content → SAME pointer */
    const char* a = string_intern("foo");
    const char* b = string_intern("foo");

    cr_assert_not_null(a);
    cr_assert_eq(a, b, "intern('foo') must return same pointer");
}

Test(interning, distinct, .init = setup, .fini = teardown) {
    /* DIFFERENT content → DIFFERENT pointers */
    const char* a = string_intern("foo");
    const char* b = string_intern("bar");

    cr_assert_not_null(a);
    cr_assert_not_null(b);
    cr_assert_neq(a, b, "Different strings must have different pointers");
}

Test(interning, nullptr_input, .init = setup, .fini = teardown) {
    /* nullptr input → nullptr output */
    const char* result = string_intern(nullptr);

    cr_assert_null(result, "intern(nullptr) must return nullptr");
}

Test(interning, empty_string, .init = setup, .fini = teardown) {
    /* Empty string is valid, internable */
    const char* a = string_intern("");
    const char* b = string_intern("");

    cr_assert_not_null(a);
    cr_assert_eq(a, b, "Empty string must intern consistently");
    cr_assert_str_eq(a, "", "Empty string content preserved");
}

Test(interning, content_preserved, .init = setup, .fini = teardown) {
    /* String content must match original */
    const char* result = string_intern("hello world");

    cr_assert_not_null(result);
    cr_assert_str_eq(result, "hello world");
}

/* ============================================================================
 * Resize behavior (CRITICAL for memory safety)
 * ============================================================================ */

Test(interning, resize_preserves_pointers, .init = setup, .fini = teardown) {
    /*
     * CRITICAL: Pointers must remain valid after hash table resize.
     *
     * Bug scenario without stable pointers:
     *   1. intern("a") returns ptr_a
     *   2. many more interns trigger resize
     *   3. ptr_a now INVALID (dangling) if strings moved
     *
     * Solution: strings stored separately, not in hash buckets.
     */
    constexpr int PRE_RESIZE = 100;
    constexpr int POST_RESIZE = 1000;

    const char* ptrs[PRE_RESIZE];

    /* Store pointers before resize */
    for (int i = 0; i < PRE_RESIZE; i++) {
        char buf[32];
        snprintf(buf, sizeof(buf), "string_%d", i);
        ptrs[i] = string_intern(buf);
        cr_assert_not_null(ptrs[i]);
    }

    /* Force multiple resizes */
    for (int i = PRE_RESIZE; i < POST_RESIZE; i++) {
        char buf[32];
        snprintf(buf, sizeof(buf), "string_%d", i);
        (void)string_intern(buf);  /* [[nodiscard]] but intentionally unused */
    }

    /* Verify ALL original pointers still valid and correct */
    for (int i = 0; i < PRE_RESIZE; i++) {
        char buf[32];
        snprintf(buf, sizeof(buf), "string_%d", i);

        /* Same content → same pointer */
        const char* again = string_intern(buf);
        cr_assert_eq(ptrs[i], again,
            "Pointer for 'string_%d' changed after resize", i);

        /* Content still correct */
        cr_assert_str_eq(ptrs[i], buf,
            "Content for 'string_%d' corrupted after resize", i);
    }
}

/* ============================================================================
 * Scale and memory bounds
 * ============================================================================ */

Test(interning, intern_many_unique, .init = setup, .fini = teardown) {
    /* 10K unique strings should work */
    constexpr int COUNT = 10000;

    for (int i = 0; i < COUNT; i++) {
        char buf[64];
        snprintf(buf, sizeof(buf), "/path/to/module_%d.py", i);
        const char* result = string_intern(buf);
        cr_assert_not_null(result);
    }

    size_t count = string_table_count();
    cr_assert_eq(count, COUNT, "Expected %d strings, got %zu", COUNT, count);
}

Test(interning, intern_many_duplicates, .init = setup, .fini = teardown) {
    /*
     * 1M calls with only 1K unique strings.
     * Memory should be bounded by unique count, not call count.
     */
    constexpr int CALLS = 100000;  /* Reduced for test speed */
    constexpr int UNIQUE = 1000;

    for (int i = 0; i < CALLS; i++) {
        char buf[64];
        snprintf(buf, sizeof(buf), "/path/to/file_%d.py", i % UNIQUE);
        (void)string_intern(buf);  /* [[nodiscard]] but intentionally unused */
    }

    size_t count = string_table_count();
    cr_assert_eq(count, UNIQUE,
        "Expected %d unique strings, got %zu (memory leak?)", UNIQUE, count);
}

/* ============================================================================
 * Edge cases
 * ============================================================================ */

Test(interning, long_string, .init = setup, .fini = teardown) {
    /* Long strings should work (up to reasonable limit) */
    char long_str[4096];
    memset(long_str, 'x', sizeof(long_str) - 1);
    long_str[sizeof(long_str) - 1] = '\0';

    const char* a = string_intern(long_str);
    const char* b = string_intern(long_str);

    cr_assert_not_null(a);
    cr_assert_eq(a, b);
    cr_assert_eq(strlen(a), sizeof(long_str) - 1);
}

Test(interning, special_chars, .init = setup, .fini = teardown) {
    /* Strings with special characters */
    const char* cases[] = {
        "path/with/slashes",
        "has\ttab",
        "has\nnewline",
        "has spaces",
        "unicode: \xc3\xa9",  /* é in UTF-8 */
        "null\x00embedded",   /* Will be truncated at \0 */
    };

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        const char* a = string_intern(cases[i]);
        const char* b = string_intern(cases[i]);
        cr_assert_eq(a, b, "Special char string %zu not idempotent", i);
    }
}

Test(interning, binary_safe, .init = setup, .fini = teardown) {
    /*
     * Note: C strings are NUL-terminated.
     * string_intern uses strlen, so embedded NULs truncate.
     * This is expected behavior for C strings.
     */
    const char* a = string_intern("abc\0def");  /* Seen as "abc" */
    const char* b = string_intern("abc");

    cr_assert_eq(a, b, "NUL-terminated strings should match");
}

/* ============================================================================
 * API edge cases
 * ============================================================================ */

Test(interning, double_init_safe) {
    /* Double init should be safe (or error) */
    string_table_init(64);
    string_table_init(64);  /* Should not crash */
    string_table_destroy();
    string_table_destroy(); /* Should not crash */
}

Test(interning, use_after_destroy) {
    /*
     * Using table after destroy is UB.
     * With REQUIRE macro, should abort.
     * Test just verifies destroy doesn't crash.
     */
    string_table_init(64);
    (void)string_intern("test");  /* [[nodiscard]] but intentionally unused */
    string_table_destroy();
    /* Don't call intern after destroy - that's UB */
}
