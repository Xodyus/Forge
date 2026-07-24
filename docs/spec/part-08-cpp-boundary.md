# Part VIII - C++20 Accelerator and Python Boundary

## 118. Purpose of the C++ Extension

The C++ extension exists to demonstrate measured systems and language integration, not to decorate the repository. The first candidate workload is decoding fixed-width records and accumulating per-stream statistics over large batches. Python remains responsible for orchestration, manifests, scheduling, and analysis. C++ owns a narrow compute kernel whose inputs and outputs can be independently verified.

A pure-Python implementation remains the semantic reference. A NumPy or struct-based implementation may serve as an additional baseline. The extension is accepted only after profile data shows parsing or aggregation consumes enough time to justify the boundary.

## 119. C++ Package Layout

    cpp/
      CMakeLists.txt
      include/forge_cpp/
        event_record.hpp
        parser.hpp
        stats.hpp
        errors.hpp
        version.hpp
      src/
        parser.cpp
        stats.cpp
        bindings.cpp
      tests/
        test_parser.cpp
        test_stats.cpp
        test_errors.cpp
      benchmarks/
        bench_parse.cpp
        bench_stats.cpp
    python/forge_cpp/
      __init__.py
      _types.py
      py.typed

## 120. Public Extension API

    def stats_from_file(
        path: os.PathLike[str],
        *,
        header_bytes: int,
        record_start: int,
        record_count: int,
        event_type_mask: int,
        expected_record_bytes: int = 32,
    ) -> StatsResult: ...

    def stats_from_buffer(
        data: typing.Buffer,
        *,
        first_sequence: int | None = None,
        event_type_mask: int,
    ) -> StatsResult: ...

    def build_info() -> BuildInfo: ...

The public API is batch-oriented. Do not expose one Python-to-C++ call per record. The result may be a typed Python object containing contiguous arrays or a compact list of group records, plus counters and a canonical digest helper.

## 121. C++ Domain Types

    namespace forge {

    struct EventRecord {
        std::uint64_t sequence;
        std::int64_t timestamp_ns;
        std::uint32_t stream_id;
        std::uint16_t event_type;
        std::uint16_t flags;
        std::int64_t value;
    };

    struct StreamStats {
        std::uint32_t stream_id;
        std::uint64_t count;
        std::int64_t sum;
        std::int64_t min;
        std::int64_t max;
        std::uint64_t first_sequence;
        std::uint64_t last_sequence;
    };

    struct ParseSummary {
        std::uint64_t records_read;
        std::uint64_t records_selected;
        std::vector<StreamStats> groups;
    };

    } // namespace forge

Use checked addition for sums if generated values could overflow int64. Define whether overflow rejects the partition, saturates, or uses a wider accumulator such as \_\_int128 before narrowing with validation. Silent signed overflow is forbidden.

## 122. Explicit On-Disk Decoding

- Read little-endian integers with explicit helpers or safe byte-copy and conversion. Do not reinterpret unaligned bytes as a native struct.
- Validate total buffer length is a multiple of the declared record size for a raw batch.
- Check record_start and record_count multiplication for overflow before calculating offsets.
- Validate sequence or timestamp monotonicity only when the dataset contract requires it; make validation mode explicit.
- Return structured errors containing code, record index, expected/actual values, and bounded context.
- Separate validation from hot-loop aggregation enough that benchmarks can compare standard and strict modes honestly.

## 123. Batch Size and Call Boundary

The boundary should amortize Python call, argument conversion, error translation, and result construction. Benchmark several batch sizes rather than choosing one by intuition.

**Table 50 --- C++ batch boundary alternatives.**

  -------------------------------------------------------------------------------------------------------------------
  Batch strategy            Advantage                                Risk
  ------------------------- ---------------------------------------- ------------------------------------------------
  Whole partition           Fewest crossings and simple API          High peak memory or long cancellation latency.

  Fixed records per batch   Bounded memory and responsive progress   More crossings; final short batch.

  Fixed bytes per batch     Aligns with I/O and cache experiments    Record alignment must be enforced.

  Memory-mapped view        Avoid explicit read copy                 Page faults, lifetime, and mapping complexity.

  Shared-memory slot        Potential zero-copy local pipeline       Ownership and synchronization complexity.
  -------------------------------------------------------------------------------------------------------------------

## 124. Buffer Protocol and Ownership

- Accept read-only contiguous bytes-like objects through pybind11 buffer protocol and validate format, item size, dimensions, strides, and total length.
- Hold a Python reference or py::buffer_info lifetime while C++ reads the memory; never retain a raw pointer after the call unless a documented owner object persists.
- For result arrays, either copy into Python-owned objects or expose a capsule whose destructor owns the allocation safely.
- Avoid returning views into stack memory, temporary vectors, or unmapped files.
- Document whether output order is sorted by stream_id and use that order for canonicalization.
- Measure copies explicitly. A zero-copy design is not automatically faster if it creates page faults or complicated lifetimes.

## 125. GIL Policy

- Validate Python arguments and obtain stable buffer/path information while holding the GIL.
- Release the GIL around long file reads, decoding, and aggregation that do not touch Python objects.
- Reacquire the GIL before constructing Python result objects or raising translated exceptions.
- Do not call Python progress callbacks from the hot loop in the first implementation; use coarse batch boundaries if progress is needed.
- If the C++ kernel uses threads later, state how it interacts with worker process concurrency and avoid oversubscription.
- Test a Python thread making progress while the C++ call runs to verify release behavior, but do not confuse that with a performance guarantee.

## 126. Exception Translation

**Table 51 --- C++ to Python error translation.**

  ---------------------------------------------------------------------------------------------------------------------------
  C++ condition                           Python exception     Task classification
  --------------------------------------- -------------------- --------------------------------------------------------------
  invalid_argument or schema validation   ForgeDataError       Deterministic terminal unless input policy says otherwise.

  overflow_error                          ForgeOverflowError   Deterministic terminal; include record/group context.

  filesystem read error                   ForgeIOError         Retryable or terminal according to errno and storage policy.

  bad_alloc                               MemoryError          Resource failure; retry only if another profile can succeed.

  internal logic_error/invariant          ForgeInternalError   Fail closed and capture diagnostics.

  unknown exception                       ForgeCppError        Internal failure; never terminate interpreter silently.
  ---------------------------------------------------------------------------------------------------------------------------

## 127. Reference Aggregation Algorithm

    def reference_stats(records: Iterable[Event], mask: int) -> list[StreamStats]:
        groups: dict[int, MutableStats] = {}
        for record in records:
            if not (mask & (1 << record.event_type)):
                continue
            stats = groups.setdefault(record.stream_id, MutableStats.empty())
            stats.add(record)
        return [groups[key].freeze() for key in sorted(groups)]

Keep this implementation intentionally straightforward and structurally independent. It should not call the C++ parser, reuse the C++ result canonicalizer blindly, or depend on the same unsafe byte-decoding helper. Independence makes differential tests meaningful.

## 128. C++ Aggregation Data Structure Choices

**Table 52 --- C++ aggregation structure experiments.**

  --------------------------------------------------------------------------------------------------------------------------------------------
  Choice                                   When appropriate                                Experiment question
  ---------------------------------------- ----------------------------------------------- ---------------------------------------------------
  std::unordered_map\<stream_id, stats\>   Unknown or sparse stream IDs                    Hash cost, allocation count, reserve behavior.

  Dense vector indexed by stream_id        Known bounded dense range                       Memory versus cache locality and branch behavior.

  Sort then reduce                         Large batch and output already needs ordering   Sorting cost versus hash allocations.

  Small-vector then fallback map           Few groups per partition                        Complexity versus real workload distribution.

  Structure of arrays                      Vectorized output or repeated scans             Cache behavior and result construction cost.
  --------------------------------------------------------------------------------------------------------------------------------------------

Start with the simplest correct representation that matches the generator bounds. If stream IDs are 0..N-1 and N is modest, a dense vector plus touched-index list may be both simpler and faster than a hash table. The README should explain the workload assumption instead of presenting one structure as universally superior.

## 129. Memory Allocation Strategy

- Reserve vectors when the upper bound is known and record capacity decisions.
- Avoid one heap allocation per record. Per-group allocation may still be acceptable and should be measured.
- Reuse batch-local buffers within one task only when lifecycle remains clear.
- Do not introduce a custom allocator before allocation profiles show a meaningful cost.
- Run AddressSanitizer and UndefinedBehaviorSanitizer on the extension and native tests.
- Use Valgrind or heap profiling selectively; disclose its overhead and avoid using instrumented timings as performance results.

## 130. SIMD and Parallelism Policy

SIMD or internal threading is optional research. Fixed records include mixed-width fields and conditional grouping, so auto-vectorization may be limited. Measure compiler reports and hardware counters before writing intrinsics.

- Establish scalar C++ correctness and a stable benchmark first.
- Inspect generated assembly or compiler vectorization reports for candidate loops.
- Separate byte swapping/validation from aggregation if it improves vectorization without duplicating scans excessively.
- Any SIMD path requires a scalar fallback and differential tests across unaligned and tail lengths.
- Internal threads must default off and expose thread count in the run and benchmark manifests.
- Scaling reports must avoid multiplying worker count by hidden C++ thread count accidentally.

## 131. Build and Packaging

- Use CMake with a modern target-based configuration and pybind11 through a pinned dependency.
- Use scikit-build-core or another reproducible PEP 517 backend to build the extension into the Python package.
- Expose compiler, build type, flags, git commit, and extension version through build_info().
- Compile with high warnings and treat project warnings as errors in CI, while not forcing third-party warnings.
- Provide debug, release, ASan/UBSan, and benchmark presets.
- Do not publish a wheel until supported Python/OS/architecture scope is tested. A source-build project is acceptable if documented.
- Keep the extension optional for reference-mode installation when practical; fail clearly when a C++ kernel is requested without it.

## 132. ABI and Compatibility

- Treat the Python extension as versioned with the Forge package; do not promise a stable C++ ABI.
- Encode dataset and result schema compatibility separately from extension binary compatibility.
- At import, verify expected extension API version and expose a clear mismatch error.
- A worker advertises the logical kernel version plus exact extension build digest.
- Clean rebuilds are required after compiler, Python minor version, pybind11 major version, or C++ standard-library changes unless compatibility is proven.

## 133. C++ Verification Plan

- Native unit tests for endian decoding, bounds, masks, every aggregation field, overflow, and empty input.
- Python differential tests against the independent reference for generated records and partition boundaries.
- Property tests varying batch size, alignment, group distribution, event masks, values, and sequence ranges.
- Fuzz parser entry points with arbitrary bytes, valid-prefix mutations, short buffers, and extreme lengths.
- ASan and UBSan in CI; ThreadSanitizer only if internal threading is added and compatible.
- Tests for Python exception types, messages, and absence of interpreter crashes.
- Buffer-lifetime tests that release original objects only after calls complete and detect accidental retained pointers.
- Cross-implementation canonical digest equality for all public workload seeds.

## 134. C++ Benchmark Plan

**Table 53 --- C++ and boundary benchmarks.**

  ----------------------------------------------------------------------------------------------------------------------------
  Benchmark             Comparison                                             Primary metric
  --------------------- ------------------------------------------------------ -----------------------------------------------
  parse-buffer          Python struct/unpack or NumPy versus scalar C++        records/s and CPU cycles/record

  aggregate-dense       Python reference, NumPy candidate, C++ dense vector    records/s and peak memory

  aggregate-sparse      C++ unordered_map versus sort/reduce                   cycles/record and allocations

  batch-size            4 KiB through whole partition                          throughput, p99 batch time, boundary overhead

  file-reader           buffered read versus pread versus mmap                 throughput, faults, CPU, RSS

  GIL                   C++ call with and without release in controlled test   other-thread progress and overhead

  result-construction   list of objects versus arrays/compact bytes            time and Python allocation count

  strict-validation     fast versus strict parser checks                       cost per record and error coverage
  ----------------------------------------------------------------------------------------------------------------------------

A valid conclusion may be that file I/O, Python result construction, or coordinator overhead dominates after the C++ loop is optimized. Document the bottleneck shift rather than continuing to optimize the old hotspot.

## 135. C++ Acceptance Criteria

- The extension is optional for reference-mode installation and required only for selected kernels.
- All native and Python differential tests pass for the published seed corpus.
- ASan and UBSan runs are clean.
- The GIL is released only around code that does not touch Python objects.
- No raw pointer outlives its documented owner.
- Build metadata is visible and included in run fingerprints.
- The benchmark report identifies the exact workload where C++ helps, the cost of crossing the boundary, and any case where it does not help.
- The README avoids a generic faster than Python claim and links to raw results.
