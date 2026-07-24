# Appendix H - C++20 Accelerator and pybind11 Skeleton

## 393. Native Boundary Acceptance Contract

- The extension accelerates one profile-selected operation and does not reimplement coordinator semantics.
- The Python reference remains available and is the correctness oracle.
- The public API is batch-oriented and validates all buffer metadata before native iteration.
- Input ownership is explicit. A borrowed view is used only for the duration of the call while the Python owner remains alive, or the data is copied into owned storage.
- The GIL is released only after validation and only while no Python C API is used.
- Native exceptions translate to stable Python exception classes after the GIL is held.
- All size and offset arithmetic is checked before pointer addition, allocation, or loop bounds.
- Optimized and scalar paths produce identical canonical results for the supported integer schema.
- Debug, ASan, UBSan, and optimized builds are separated; benchmark evidence uses recorded release flags.
- The extension version, compiler, build mode, and selected engine are recorded in the run manifest.

## 394. C++ Event and Result Types

    #pragma once

    #include <cstddef>
    #include <cstdint>
    #include <span>
    #include <stdexcept>
    #include <string>
    #include <unordered_map>
    #include <vector>

    namespace forge::core {

    inline constexpr std::size_t kEventBytes = 32;

    struct Event final {
      std::uint64_t timestamp_ns;
      std::uint32_t instrument_id;
      std::uint8_t event_type;
      std::uint8_t flags;
      std::uint16_t reserved;
      std::int64_t value_i64;
      std::uint32_t quantity;
      std::uint32_t sequence;
    };

    static_assert(sizeof(Event) == kEventBytes);
    static_assert(std::is_trivially_copyable_v<Event>);

    struct InstrumentStats final {
      std::uint64_t event_count{0};
      std::int64_t value_sum{0};
      std::uint64_t quantity_sum{0};
    };

    using StatsMap = std::unordered_map<std::uint32_t, InstrumentStats>;

    class DecodeError final : public std::runtime_error {
     public:
      using std::runtime_error::runtime_error;
    };

    class OverflowError final : public std::runtime_error {
     public:
      using std::runtime_error::runtime_error;
    };

    StatsMap aggregate_events(std::span<const std::byte> bytes);

    }  // namespace forge::core

Directly reinterpreting file bytes as `Event` is only safe when byte order, alignment, object representation, and packing assumptions are guaranteed. A robust implementation should decode little-endian fields explicitly or use `memcpy` into scalar fields, especially if portability is part of the contract. The `static_assert` above is an educational signal, not a substitute for a documented wire-format decoder.

## 395. Checked Little-Endian Decoder

    #include "forge/core/event.hpp"

    #include <bit>
    #include <cstring>
    #include <limits>
    #include <type_traits>

    namespace forge::core {
    namespace {

    template <typename T>
    [[nodiscard]] T load_little_endian(const std::byte* source) {
      static_assert(std::is_integral_v<T>);
      T value{};
      std::memcpy(&value, source, sizeof(T));
      if constexpr (std::endian::native == std::endian::big) {
        value = std::byteswap(value);  // C++23; provide C++20 helper in project.
      }
      return value;
    }

    [[nodiscard]] Event decode_event(const std::byte* p) {
      Event event{};
      event.timestamp_ns = load_little_endian<std::uint64_t>(p + 0);
      event.instrument_id = load_little_endian<std::uint32_t>(p + 8);
      event.event_type = std::to_integer<std::uint8_t>(p[12]);
      event.flags = std::to_integer<std::uint8_t>(p[13]);
      event.reserved = load_little_endian<std::uint16_t>(p + 14);
      event.value_i64 = load_little_endian<std::int64_t>(p + 16);
      event.quantity = load_little_endian<std::uint32_t>(p + 24);
      event.sequence = load_little_endian<std::uint32_t>(p + 28);
      if (event.reserved != 0) {
        throw DecodeError("event reserved field is nonzero");
      }
      return event;
    }

    void checked_add(std::int64_t& destination, std::int64_t value) {
      if ((value > 0 && destination > std::numeric_limits<std::int64_t>::max() - value) ||
          (value < 0 && destination < std::numeric_limits<std::int64_t>::min() - value)) {
        throw OverflowError("signed aggregation overflow");
      }
      destination += value;
    }

    void checked_add(std::uint64_t& destination, std::uint64_t value) {
      if (destination > std::numeric_limits<std::uint64_t>::max() - value) {
        throw OverflowError("unsigned aggregation overflow");
      }
      destination += value;
    }

    }  // namespace

    StatsMap aggregate_events(std::span<const std::byte> bytes) {
      if (bytes.size() % kEventBytes != 0) {
        throw DecodeError("input byte length is not a whole number of records");
      }

      const std::size_t record_count = bytes.size() / kEventBytes;
      StatsMap result;
      result.reserve(record_count < 4096 ? record_count : 4096);

      for (std::size_t index = 0; index < record_count; ++index) {
        const std::byte* record = bytes.data() + index * kEventBytes;
        const Event event = decode_event(record);
        auto& stats = result[event.instrument_id];
        checked_add(stats.event_count, std::uint64_t{1});
        checked_add(stats.value_sum, event.value_i64);
        checked_add(stats.quantity_sum,
                    static_cast<std::uint64_t>(event.quantity));
      }
      return result;
    }

    }  // namespace forge::core

Because `std::byteswap` is standardized in C++23, the actual C++20 implementation needs a small tested byte-swap helper or compiler intrinsics behind a portable wrapper. The source should not claim strict C++20 while silently relying on a newer library API.

## 396. pybind11 Boundary

    #include "forge/core/event.hpp"

    #include <pybind11/pybind11.h>
    #include <pybind11/pytypes.h>

    #include <cstddef>
    #include <span>
    #include <string>

    namespace py = pybind11;

    namespace {

    py::dict aggregate_buffer(py::buffer buffer) {
      py::buffer_info info = buffer.request(/*writable=*/false);
      if (info.ndim != 1) {
        throw py::value_error("expected a one-dimensional byte buffer");
      }
      if (info.itemsize != 1) {
        throw py::value_error("buffer item size must be one byte");
      }
      if (info.strides.empty() || info.strides[0] != 1) {
        throw py::value_error("buffer must be contiguous");
      }
      if (info.size < 0) {
        throw py::value_error("buffer size is negative");
      }

      const auto byte_count = static_cast<std::size_t>(info.size);
      const auto* data = static_cast<const std::byte*>(info.ptr);
      std::span<const std::byte> view{data, byte_count};

      forge::core::StatsMap stats;
      {
        // The py::buffer object and buffer_info remain alive in this frame. The
        // extension does not retain data after the call. No Python API is used
        // inside the released region.
        py::gil_scoped_release release;
        stats = forge::core::aggregate_events(view);
      }

      py::dict result;
      for (const auto& [instrument_id, values] : stats) {
        py::dict row;
        row["event_count"] = values.event_count;
        row["value_sum"] = values.value_sum;
        row["quantity_sum"] = values.quantity_sum;
        result[py::int_(instrument_id)] = std::move(row);
      }
      return result;
    }

    }  // namespace

    PYBIND11_MODULE(_forge_core, module) {
      module.doc() = "Forge batch event parser and aggregation extension";

      py::register_exception<forge::core::DecodeError>(
          module, "DecodeError", PyExc_ValueError);
      py::register_exception<forge::core::OverflowError>(
          module, "OverflowError", PyExc_OverflowError);

      module.def(
          "aggregate_buffer",
          &aggregate_buffer,
          py::arg("buffer"),
          "Aggregate one contiguous batch of fixed-width Forge events.");
    }

## 397. C++ Review Checklist

- Does every pointer or span have an owner whose lifetime is obvious?
- Can a buffer be resized, released, or garbage-collected while the GIL is released?
- Are shape, item size, stride, contiguity, alignment, and length validated?
- Can multiplication or addition overflow before bounds checking?
- Are file byte order and host byte order handled explicitly?
- Can malformed input create excessive allocation through a count or instrument ID distribution?
- Are exceptions thrown across threads or destroyed after Python teardown?
- Does the binding retain references after return? If so, is `keep_alive` or owning storage correct?
- Do debug and sanitizer tests exercise empty, truncated, huge, misaligned, noncontiguous, and overflow inputs?
- Does the optimized path preserve canonical output ordering even if an unordered map is used internally?
- Is the native interface narrow enough to explain and benchmark?
- Are compiler and platform assumptions recorded in build and release evidence?

## 398. CMake Skeleton

    cmake_minimum_required(VERSION 3.24)
    project(forge LANGUAGES CXX)

    option(FORGE_BUILD_TESTS "Build native tests" ON)
    option(FORGE_ENABLE_ASAN "Enable AddressSanitizer" OFF)
    option(FORGE_ENABLE_UBSAN "Enable UndefinedBehaviorSanitizer" OFF)

    set(CMAKE_CXX_STANDARD 20)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
    set(CMAKE_CXX_EXTENSIONS OFF)

    find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
    find_package(pybind11 CONFIG REQUIRED)

    add_library(forge_core STATIC
        cpp/src/event.cpp
    )
    target_include_directories(forge_core PUBLIC cpp/include)
    target_compile_features(forge_core PUBLIC cxx_std_20)
    set_target_properties(forge_core PROPERTIES POSITION_INDEPENDENT_CODE ON)

    if(MSVC)
      target_compile_options(forge_core PRIVATE /W4 /WX /permissive-)
    else()
      target_compile_options(forge_core PRIVATE
          -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Werror)
    endif()

    if(FORGE_ENABLE_ASAN AND NOT MSVC)
      target_compile_options(forge_core PRIVATE -fsanitize=address -fno-omit-frame-pointer)
      target_link_options(forge_core PRIVATE -fsanitize=address)
    endif()

    if(FORGE_ENABLE_UBSAN AND NOT MSVC)
      target_compile_options(forge_core PRIVATE -fsanitize=undefined -fno-omit-frame-pointer)
      target_link_options(forge_core PRIVATE -fsanitize=undefined)
    endif()

    pybind11_add_module(_forge_core MODULE cpp/src/bindings.cpp)
    target_link_libraries(_forge_core PRIVATE forge_core)
    install(TARGETS _forge_core LIBRARY DESTINATION forge)

    if(FORGE_BUILD_TESTS)
      enable_testing()
      find_package(GTest CONFIG REQUIRED)
      add_executable(forge_core_tests cpp/tests/event_test.cpp)
      target_link_libraries(forge_core_tests PRIVATE forge_core GTest::gtest_main)
      include(GoogleTest)
      gtest_discover_tests(forge_core_tests)
    endif()

## 399. pyproject Build Skeleton

    [build-system]
    requires = [
      "scikit-build-core>=0.10",
      "pybind11>=2.12",
    ]
    build-backend = "scikit_build_core.build"

    [project]
    name = "forge-replay"
    version = "0.1.0"
    description = "Deterministic local-first event replay and compute engine"
    requires-python = ">=3.12"
    readme = "README.md"
    license = {file = "LICENSE"}
    authors = [{name = "Lucas Cochran"}]
    dependencies = []

    [project.optional-dependencies]
    dev = [
      "pytest>=8",
      "hypothesis>=6",
      "mypy>=1.10",
      "ruff>=0.5",
    ]

    [project.scripts]
    forge = "forge.cli:main"

    [tool.scikit-build]
    cmake.build-type = "Release"
    wheel.packages = ["src/forge"]

    [tool.pytest.ini_options]
    addopts = "-ra --strict-markers --strict-config"
    testpaths = ["tests"]
    markers = [
      "integration: crosses process or transport boundaries",
      "recovery: injects crash, timeout, or restart",
      "slow: longer-running suite",
      "benchmark_smoke: catastrophic regression check only",
    ]

    [tool.mypy]
    python_version = "3.12"
    strict = true
    mypy_path = "src"

    [tool.ruff]
    line-length = 88
    target-version = "py312"

## 400. Native Crossover Study Matrix

**Table 140 --- Native crossover experiment matrix.**

  --------------------------------------------------------------------------------------------------------------------------------------------
  Variable                 Values                                                     Purpose
  ------------------------ ---------------------------------------------------------- --------------------------------------------------------
  batch records            1, 16, 256, 4K, 64K, 1M                                    Locate call/conversion crossover.

  instrument cardinality   1, 16, 128, 4K                                             Expose hash-map and output-conversion cost.

  engine                   Python reference, Python vectorized if used, C++ scalar    Provide fair baselines.

  input ownership          bytes, memoryview, mmap slice where safe                   Measure copy and buffer acquisition.

  output shape             small aggregate, large per-key result                      Separate compute gain from Python object construction.

  build                    release only for claims; debug/sanitizer for correctness   Avoid invalid comparison.

  metric                   call ns, records/s, end-to-end run s, peak memory          Prevent microbenchmark-only conclusion.
  --------------------------------------------------------------------------------------------------------------------------------------------
