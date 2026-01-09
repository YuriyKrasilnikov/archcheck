# C23 Test Framework Makefile (Criterion)
#
# Targets:
#   test        - Run all tests (default)
#   test-asan   - Run with AddressSanitizer
#   test-tsan   - Run with ThreadSanitizer
#   test-all    - Run both ASan and TSan
#   clean       - Remove build artifacts
#
# Requires: libcriterion-dev (apt install libcriterion-dev)

# Compiler (GCC 15+ for C23 support)
CC := gcc
CSTD := -std=c23

# Paths
ROOT := ../..
C_SRC := $(ROOT)/c

# Warnings (strict)
WARNINGS := -Wall -Wextra -Wpedantic -Werror \
            -Wconversion -Wshadow -Wundef

# Includes
INCLUDES := -I$(C_SRC)

# Criterion
CRITERION := -lcriterion

# Base flags
BASE_FLAGS := $(CSTD) $(WARNINGS) $(INCLUDES) -g -O0

# Sanitizers
ASAN_FLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
TSAN_FLAGS := -fsanitize=thread -fno-omit-frame-pointer

# Threading
THREAD_FLAGS := -pthread

# Build directory
BUILD := build

# Test sources (all test_*.c files)
TEST_SRCS := $(wildcard test_*.c)

# C module sources (add as implemented)
C_SRCS := $(wildcard $(C_SRC)/interning.c) \
          $(wildcard $(C_SRC)/barrier.c) \
          $(wildcard $(C_SRC)/frame.c) \
          $(wildcard $(C_SRC)/callback.c) \
          $(wildcard $(C_SRC)/context.c)

# ============================================================================
# Targets
# ============================================================================

.PHONY: all test test-asan test-tsan test-all clean

all: test

$(BUILD):
	@mkdir -p $(BUILD)

# Plain (no sanitizers)
test: $(BUILD)
	@echo "═══ Running tests ═══"
	$(CC) $(BASE_FLAGS) $(THREAD_FLAGS) \
		$(TEST_SRCS) $(C_SRCS) \
		$(CRITERION) -o $(BUILD)/test_runner
	$(BUILD)/test_runner --verbose

# AddressSanitizer (memory errors, leaks, UB)
test-asan: $(BUILD)
	@echo "═══ Running tests (ASan + UBSan) ═══"
	$(CC) $(BASE_FLAGS) $(ASAN_FLAGS) $(THREAD_FLAGS) \
		$(TEST_SRCS) $(C_SRCS) \
		$(CRITERION) -o $(BUILD)/test_asan
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \
	UBSAN_OPTIONS=halt_on_error=1 \
		$(BUILD)/test_asan --verbose

# ThreadSanitizer (data races)
test-tsan: $(BUILD)
	@echo "═══ Running tests (TSan) ═══"
	$(CC) $(BASE_FLAGS) $(TSAN_FLAGS) $(THREAD_FLAGS) \
		$(TEST_SRCS) $(C_SRCS) \
		$(CRITERION) -o $(BUILD)/test_tsan
	TSAN_OPTIONS=halt_on_error=1 \
		$(BUILD)/test_tsan --verbose

# Full sanitizer suite
test-all: test-asan test-tsan
	@echo "═══ All sanitizer tests passed ═══"

clean:
	rm -rf $(BUILD)

# ============================================================================
# Single-file targets (for incremental development)
# ============================================================================

test-interning: $(BUILD)
	$(CC) $(BASE_FLAGS) $(ASAN_FLAGS) $(THREAD_FLAGS) \
		test_interning.c $(C_SRC)/interning.c \
		$(CRITERION) -o $(BUILD)/test_interning
	ASAN_OPTIONS=detect_leaks=1 $(BUILD)/test_interning --verbose

test-threading: $(BUILD)
	@echo "═══ TSan Tests (standalone, no Criterion) ═══"
	$(CC) $(BASE_FLAGS) $(TSAN_FLAGS) $(THREAD_FLAGS) \
		test_tsan_interning.c $(C_SRC)/interning.c \
		-o $(BUILD)/test_tsan_interning
	TSAN_OPTIONS=halt_on_error=1 $(BUILD)/test_tsan_interning

test-barrier: $(BUILD)
	@echo "═══ Stop Barrier TSan Tests (standalone, no Criterion) ═══"
	$(CC) $(BASE_FLAGS) $(TSAN_FLAGS) $(THREAD_FLAGS) \
		test_barrier.c $(C_SRC)/barrier.c \
		-o $(BUILD)/test_barrier
	TSAN_OPTIONS=halt_on_error=1 $(BUILD)/test_barrier

test-frame: $(BUILD)
	@echo "═══ Frame Stack Tests (ASan) ═══"
	$(CC) $(BASE_FLAGS) $(ASAN_FLAGS) $(THREAD_FLAGS) \
		test_frame.c $(C_SRC)/frame.c $(C_SRC)/interning.c \
		-o $(BUILD)/test_frame
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 $(BUILD)/test_frame

test-frame-tsan: $(BUILD)
	@echo "═══ Frame Stack TSan Tests ═══"
	$(CC) $(BASE_FLAGS) $(TSAN_FLAGS) $(THREAD_FLAGS) \
		test_frame.c $(C_SRC)/frame.c $(C_SRC)/interning.c \
		-o $(BUILD)/test_frame_tsan
	TSAN_OPTIONS=halt_on_error=1 $(BUILD)/test_frame_tsan

test-callback: $(BUILD)
	@echo "═══ Event Callback Tests (ASan) ═══"
	$(CC) $(BASE_FLAGS) $(ASAN_FLAGS) $(THREAD_FLAGS) \
		test_callback.c $(C_SRC)/callback.c $(C_SRC)/barrier.c $(C_SRC)/interning.c $(C_SRC)/context.c \
		-o $(BUILD)/test_callback
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 $(BUILD)/test_callback

test-callback-tsan: $(BUILD)
	@echo "═══ Event Callback TSan Tests ═══"
	$(CC) $(BASE_FLAGS) $(TSAN_FLAGS) $(THREAD_FLAGS) \
		test_callback.c $(C_SRC)/callback.c $(C_SRC)/barrier.c $(C_SRC)/interning.c $(C_SRC)/context.c \
		-o $(BUILD)/test_callback_tsan
	TSAN_OPTIONS=halt_on_error=1 $(BUILD)/test_callback_tsan

test-context: $(BUILD)
	@echo "═══ Context Module Tests (ASan) ═══"
	$(CC) $(BASE_FLAGS) $(ASAN_FLAGS) $(THREAD_FLAGS) \
		test_context.c $(C_SRC)/context.c \
		-o $(BUILD)/test_context
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 $(BUILD)/test_context

test-context-tsan: $(BUILD)
	@echo "═══ Context Module TSan Tests ═══"
	$(CC) $(BASE_FLAGS) $(TSAN_FLAGS) $(THREAD_FLAGS) \
		test_context.c $(C_SRC)/context.c \
		-o $(BUILD)/test_context_tsan
	TSAN_OPTIONS=halt_on_error=1 $(BUILD)/test_context_tsan

# ============================================================================
# Help
# ============================================================================

help:
	@echo "C23 Test Suite (Criterion)"
	@echo ""
	@echo "Targets:"
	@echo "  test          Run all tests"
	@echo "  test-asan     AddressSanitizer + UBSan"
	@echo "  test-tsan     ThreadSanitizer"
	@echo "  test-all      Both ASan and TSan"
	@echo ""
	@echo "Single-file:"
	@echo "  test-interning  StringTable (ASan)"
	@echo "  test-threading  Concurrency (TSan)"
	@echo "  test-barrier    Stop barrier (TSan)"
	@echo "  test-context    Context module (ASan)"
	@echo "  test-callback   Event callback (ASan)"
