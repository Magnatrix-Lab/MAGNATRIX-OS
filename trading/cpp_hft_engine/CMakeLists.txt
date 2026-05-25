# ═══════════════════════════════════════════════════════════════════════════════
# MAGNATRIX-OS — C++ HFT Engine
# Build: cmake -Bbuild -S. && cmake --build build --config Release
# ═══════════════════════════════════════════════════════════════════════════════

cmake_minimum_required(VERSION 3.18)
project(magnatrix_hft_engine VERSION 0.9.5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Build Options ─────────────────────────────────────────────────────────────
option(BUILD_PYTHON_BINDINGS "Build pybind11 Python bindings" ON)
option(BUILD_TESTS "Build unit tests" ON)
option(BUILD_SHARED "Build as shared library" OFF)
option(ENABLE_AVX2 "Enable AVX2 optimizations" OFF)
option(ENABLE_SSE4 "Enable SSE4.2 optimizations" ON)

# ── Compiler Flags ────────────────────────────────────────────────────────────
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(
        -Wall -Wextra -Wpedantic
        -O3
        -march=native
        -ffast-math
        -fomit-frame-pointer
        -funroll-loops
    )
    if(ENABLE_AVX2)
        add_compile_options(-mavx2 -mfma)
    endif()
    if(ENABLE_SSE4)
        add_compile_options(-msse4.2)
    endif()
    # Link-time optimization
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)
elseif(MSVC)
    add_compile_options(/W4 /O2 /arch:AVX2)
endif()

# ── Include Directories ───────────────────────────────────────────────────────
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# ── Source Files ──────────────────────────────────────────────────────────────
set(HFT_SOURCES
    src/order_book.cpp
    src/arbitrage_detector.cpp
    src/hft_engine.cpp
)

set(HFT_HEADERS
    include/market_data.h
    include/order_book.h
    include/arbitrage_detector.h
    include/hft_engine.h
)

# ── Static Library ────────────────────────────────────────────────────────────
add_library(magnatrix_hft STATIC ${HFT_SOURCES})
target_include_directories(magnatrix_hft PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
set_target_properties(magnatrix_hft PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)

# ── Python Bindings (pybind11) ────────────────────────────────────────────────
if(BUILD_PYTHON_BINDINGS)
    find_package(pybind11 QUIET)
    if(NOT pybind11_FOUND)
        # Fetch pybind11 if not installed
        include(FetchContent)
        FetchContent_Declare(
            pybind11
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG v2.12.0
        )
        FetchContent_MakeAvailable(pybind11)
    endif()

    pybind11_add_module(_hft_engine src/bindings.cpp)
    target_link_libraries(_hft_engine PRIVATE magnatrix_hft)
    set_target_properties(_hft_engine PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        CXX_VISIBILITY_PRESET hidden
    )
endif()

# ── Unit Tests ────────────────────────────────────────────────────────────────
if(BUILD_TESTS)
    add_executable(test_order_book tests/test_order_book.cpp)
    target_link_libraries(test_order_book PRIVATE magnatrix_hft)
    add_test(NAME order_book COMMAND test_order_book)
endif()

# ── Install ───────────────────────────────────────────────────────────────────
install(TARGETS magnatrix_hft
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)
install(FILES ${HFT_HEADERS} DESTINATION include/magnatrix/hft)
