cmake_minimum_required(VERSION 4.0)
project(archcheck LANGUAGES C)

# Options
option(ENABLE_ANALYSIS "Enable static analysis (clang-tidy)" OFF)
option(ENABLE_SANITIZERS "Enable ASan + UBSan" OFF)

# C23 standard (required, no fallback)
set(CMAKE_C_STANDARD 23)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

# Warnings
add_compile_options(-Wall -Wextra -Wpedantic)

# Static analysis
if(ENABLE_ANALYSIS)
    find_program(CLANG_TIDY clang-tidy)
    if(CLANG_TIDY)
        set(CMAKE_C_CLANG_TIDY
            ${CLANG_TIDY}
            -checks=-*,bugprone-*,cert-*,readability-function-cognitive-complexity
            --warnings-as-errors=*
        )
    endif()
endif()

# Sanitizers
if(ENABLE_SANITIZERS)
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address,undefined)
endif()

# Find Python
find_package(Python 3.14 REQUIRED COMPONENTS Interpreter Development.Module)

# C extension module
python_add_library(_tracking MODULE c/_tracking.c WITH_SOABI)

# Install to archcheck package
install(TARGETS _tracking DESTINATION archcheck)
