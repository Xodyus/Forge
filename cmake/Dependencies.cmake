# Native dependency acquisition (§257). Prefers a build-environment-provided package
# (scikit-build-core adds pybind11's CMake config to CMAKE_PREFIX_PATH automatically
# when pybind11 is listed in [build-system] requires) and falls back to FetchContent
# so a plain `cmake --preset` build stays self-sufficient for contributors who are not
# going through the Python packaging path.

include_guard(GLOBAL)

function(forge_require_pybind11)
  find_package(pybind11 CONFIG QUIET)
  if(NOT pybind11_FOUND)
    message(STATUS "pybind11 not found via find_package; fetching pinned release")
    include(FetchContent)
    FetchContent_Declare(
      pybind11
      GIT_REPOSITORY https://github.com/pybind/pybind11.git
      GIT_TAG        v2.13.6
      GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(pybind11)
  endif()
endfunction()

function(forge_require_googletest)
  include(FetchContent)
  set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
  FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG        v1.15.2
    GIT_SHALLOW    TRUE
  )
  FetchContent_MakeAvailable(googletest)
endfunction()

function(forge_require_benchmark)
  include(FetchContent)
  set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
  set(BENCHMARK_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)
  FetchContent_Declare(
    googlebenchmark
    GIT_REPOSITORY https://github.com/google/benchmark.git
    GIT_TAG        v1.9.1
    GIT_SHALLOW    TRUE
  )
  FetchContent_MakeAvailable(googlebenchmark)
endfunction()
