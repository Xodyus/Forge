#include <benchmark/benchmark.h>

#include "forge_cpp/core.hpp"

// forge_cpp_bench: Google Benchmark native microbenchmarks (§38, §254). Week 1
// scaffold: proves the benchmark target builds and runs before any real parser or
// aggregator hot path exists to measure (§269 critical path item 7 — measure before
// choosing the C++ boundary, not before you can measure at all).

static void BM_ForgeCoreAdd(benchmark::State& state) {
  std::int64_t lhs = 1;
  std::int64_t rhs = 1;
  for (auto _ : state) {
    benchmark::DoNotOptimize(lhs = forge::core::add(lhs, rhs));
  }
}
BENCHMARK(BM_ForgeCoreAdd);

BENCHMARK_MAIN();
