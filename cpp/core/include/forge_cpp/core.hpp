#pragma once

#include <cstdint>

// forge_cpp_core: native parser and aggregation library, no Python dependency (§38,
// §254). Week 1 scaffold: a single trivial function proves the build and the
// pybind11 binding path (item 4) before any real parsing or aggregation logic exists.

namespace forge::core {

[[nodiscard]] std::int64_t add(std::int64_t lhs, std::int64_t rhs) noexcept;

}  // namespace forge::core
