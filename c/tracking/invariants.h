/**
 * FAIL-FIRST Invariant Macros
 *
 * Policy: Invalid state → abort() immediately.
 * NO fallbacks, NO recovery, NO silent failures.
 *
 * C23 features: [[noreturn]], __VA_OPT__
 */

#ifndef TRACKING_INVARIANTS_H
#define TRACKING_INVARIANTS_H

#include <stdio.h>
#include <stdlib.h>

/**
 * REQUIRE: Precondition check. Aborts if condition false.
 *
 * Usage:
 *   REQUIRE(ptr != nullptr, "pointer must not be null");
 *   REQUIRE(count <= capacity, "count exceeds capacity");
 */
#define REQUIRE(cond, msg)                                                     \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr,                                                    \
                "INVARIANT VIOLATED: %s\n"                                     \
                "  condition: %s\n"                                            \
                "  at %s:%d in %s()\n",                                        \
                (msg), #cond, __FILE__, __LINE__, __func__);                   \
            abort();                                                           \
        }                                                                      \
    } while (0)

/**
 * ENSURE: Postcondition check. Aborts if condition false.
 *
 * Usage:
 *   result = compute();
 *   ENSURE(result != nullptr, "compute must return non-null");
 */
#define ENSURE(cond, msg) REQUIRE((cond), (msg))

/**
 * UNREACHABLE: Code path that should never execute.
 *
 * Usage:
 *   switch (kind) {
 *       case A: ...; break;
 *       case B: ...; break;
 *       default: UNREACHABLE("invalid event kind");
 *   }
 */
#define UNREACHABLE(msg)                                                       \
    do {                                                                       \
        fprintf(stderr,                                                        \
            "UNREACHABLE CODE REACHED: %s\n"                                   \
            "  at %s:%d in %s()\n",                                            \
            (msg), __FILE__, __LINE__, __func__);                              \
        abort();                                                               \
    } while (0)

/**
 * ASSERT_INITIALIZED: Check module initialized before use.
 *
 * Usage:
 *   ASSERT_INITIALIZED(g_table.buckets != nullptr, "StringTable");
 */
#define ASSERT_INITIALIZED(cond, module_name)                                  \
    REQUIRE((cond), module_name " not initialized")

#endif /* TRACKING_INVARIANTS_H */
