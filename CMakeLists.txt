cmake_minimum_required(VERSION 3.26)

project(forge_cpp
  LANGUAGES CXX
  DESCRIPTION "Forge native accelerator: C++20 parsing and aggregation extension"
)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(CompilerWarnings)
include(Dependencies)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)  # §255: disable compiler extensions unless documented otherwise
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(FORGE_BUILD_BINDINGS "Build the pybind11 forge_cpp extension module" ON)
option(FORGE_BUILD_TESTS "Build forge_cpp_tests (GoogleTest)" OFF)
option(FORGE_BUILD_BENCH "Build forge_cpp_bench (Google Benchmark)" OFF)
option(FORGE_WARNINGS_AS_ERRORS "Treat warnings as errors (§255, on in CI)" ON)

# forge_cpp_core — native parser and aggregation library, no Python dependency (§254).
add_library(forge_cpp_core STATIC
  cpp/core/src/core.cpp
)
target_include_directories(forge_cpp_core PUBLIC
  "${CMAKE_CURRENT_SOURCE_DIR}/cpp/core/include"
)
target_compile_features(forge_cpp_core PUBLIC cxx_std_20)
forge_set_warnings(forge_cpp_core)

# forge_cpp_bindings — pybind11 extension module named forge_cpp (§254).
if(FORGE_BUILD_BINDINGS)
  find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
  forge_require_pybind11()

  pybind11_add_module(forge_cpp cpp/bindings/module.cpp)
  target_link_libraries(forge_cpp PRIVATE forge_cpp_core)
  forge_set_warnings(forge_cpp)

  # Installed at wheel root: forge_cpp is imported as a top-level module, a sibling
  # of the forge package, not forge.forge_cpp (§38 component inventory).
  install(TARGETS forge_cpp LIBRARY DESTINATION .)
endif()

# forge_cpp_tests — GoogleTest native unit tests (§254).
if(FORGE_BUILD_TESTS)
  forge_require_googletest()
  enable_testing()
  include(GoogleTest)

  add_executable(forge_cpp_tests cpp/tests/test_core.cpp)
  target_link_libraries(forge_cpp_tests PRIVATE forge_cpp_core GTest::gtest_main)
  forge_set_warnings(forge_cpp_tests)
  gtest_discover_tests(forge_cpp_tests)
endif()

# forge_cpp_bench — Google Benchmark native microbenchmarks (§254).
if(FORGE_BUILD_BENCH)
  forge_require_benchmark()

  add_executable(forge_cpp_bench cpp/bench/bench_core.cpp)
  target_link_libraries(forge_cpp_bench PRIVATE forge_cpp_core benchmark::benchmark)
  forge_set_warnings(forge_cpp_bench)
endif()
