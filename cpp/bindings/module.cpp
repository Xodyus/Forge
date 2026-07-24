#include <pybind11/pybind11.h>

#include "forge_cpp/core.hpp"

// forge_cpp_bindings: the pybind11 extension module (§38, §254). Week 1 scaffold:
// binds only the trivial forge::core::add function to prove the Python/C++20
// boundary works end to end. No batches, buffers, or GIL policy yet — that is the
// real Part VIII work, done later and by hand.

PYBIND11_MODULE(forge_cpp, module) {
  module.doc() = "Forge native extension (Week 1 scaffold: build/binding path only)";
  module.def("add", &forge::core::add, pybind11::arg("lhs"), pybind11::arg("rhs"),
             "Trivial scaffold function proving the pybind11 boundary works.");
}
