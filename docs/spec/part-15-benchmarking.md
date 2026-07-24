# Part XV - Benchmarking, Profiling, and Performance Study

## 224. Benchmark Questions

- How much fixed overhead does the coordinator and task lifecycle add per partition?
- How does throughput scale from one to two, four, and eight workers for Python and C++ kernels?
- At what partition size does scheduling overhead stop dominating without creating unacceptable stragglers or retry cost?
- Where are bytes copied or serialized, and does changing the data path improve the measured workload?
- How much time is spent in input, parse, compute, output, digest, metadata, and waiting?
- How does strict integrity checking change throughput and CPU use?
- What is the cost and benefit of the C++ boundary at different batch sizes?
- How long do detection, lease expiry, retry, and recovery take under named failures?
- What bottleneck appears after the first optimization moves the original hotspot?

## 225. Benchmark Integrity Rules

- Freeze source commit, build type, dependencies, workload manifest, configuration, and environment fingerprint.
- Use release builds with assertions policy disclosed; never publish debug or sanitizer timing as normal performance.
- Separate warm-up from measured iterations and record every sample.
- Control or record CPU affinity, frequency policy, thermal state, memory pressure, and background load.
- Run comparisons in randomized or interleaved order when drift is plausible.
- Keep raw results immutable. Analysis produces derived files and exclusion records, not edited source rows.
- Repeat enough times to show variability and confidence, not only the best run.
- Report limits: one machine, synthetic data, filesystem cache state, and durability mode.

## 226. Benchmark Environment Record

**Table 74 --- Benchmark environment fingerprint.**

  --------------------------------------------------------------------------------------------------------------------
  Category                       Fields
  ------------------------------ -------------------------------------------------------------------------------------
  Source                         commit, tag, dirty flag, submodule/dependency lock digests

  Python                         implementation, version, build, virtual environment lock

  C++                            compiler, version, standard library, flags, CMake preset, extension build info

  OS                             distribution, kernel, container/VM status, relevant sysctls

  CPU                            model, sockets, physical/logical cores, cache sizes, governor/frequency, affinity

  Memory                         installed and available memory, NUMA topology if relevant

  Storage                        filesystem, device class, mount options, free space, cache policy

  Runtime                        workers, partition size, batch size, transport, integrity, durability, lease policy

  Study                          warmups, repetitions, order randomization, raw schema, timestamp
  --------------------------------------------------------------------------------------------------------------------

## 227. Workload Families

**Table 75 --- Benchmark workload families.**

  -------------------------------------------------------------------------------------------------------------------------------------
  Workload                      Purpose                                                     Key parameters
  ----------------------------- ----------------------------------------------------------- -------------------------------------------
  W0 no-op task                 Isolate coordinator, lease, protocol, and commit overhead   task count, tiny result, worker count

  W1 scan/count                 Measure file read and minimal parsing                       records, file split, reader, cache state

  W2 filtered stats             Representative parse and group aggregation                  streams, event mask, value distribution

  W3 sparse groups              Stress hash/group allocation                                large stream ID range, few records/group

  W4 dense groups               Stress dense accumulator and output construction            bounded dense stream IDs

  W5 skewed partitions          Study long tails and scheduling                             hot partitions, variable selected ratio

  W6 large output               Stress staging, digest, verification, and merge             groups and result bytes

  W7 fault workload             Measure detection/retry/recovery                            fault point, occurrence, lease settings

  W8 protocol micro             Measure framing and transport independent of storage        payload bytes, UDS/TCP, message rate

  W9 shared-memory experiment   Measure copy/serialization alternative                      slot bytes, batch size, producer/consumer
  -------------------------------------------------------------------------------------------------------------------------------------

## 228. Frozen Workload Manifest

    schema: forge.benchmark_workload.v1
    name: filtered-stats-100m
    dataset_manifest_sha256: "..."
    kernel: telemetry.stats_by_stream@1.0.0
    implementations: [python, cpp]
    workers: [1, 2, 4, 8]
    partition_records: [100000, 1000000, 10000000]
    batch_records: [4096, 65536, 1048576]
    transport: [embedded, unix]
    integrity: standard
    durability: standard
    warmups: 2
    repetitions: 10
    randomize_order: true
    seed: 42017

## 229. Baseline Matrix

- Reference single-process pure Python.
- Single worker through the coordinator using Python kernel.
- N workers through the coordinator using Python kernel.
- Single worker using C++ kernel.
- N workers using C++ kernel.
- Embedded queue versus Unix-domain socket for the same kernel.
- Optional loopback TCP, mmap, or shared-memory variant only after baseline publication.
- No-op task benchmark to subtract or understand fixed orchestration cost.

## 230. Primary Metrics

**Table 76 --- Primary benchmark metrics.**

  ------------------------------------------------------------------------------------------------------------------------
  Metric                         Definition
  ------------------------------ -----------------------------------------------------------------------------------------
  run wall time                  submit accepted to final committed result, with planning optionally reported separately

  steady processing throughput   logical input records / measured processing interval

  useful throughput              records in committed attempts / wall time

  attempt throughput             all attempted records including duplicate/lost work / wall time

  task latency                   lease issued to commit or terminal failure

  scheduler overhead             no-op task completion cost and coordinator CPU per committed task

  scaling speedup                T1 / TN under same workload and configuration except worker count

  parallel efficiency            speedup / N

  duplicate work ratio           noncommitted attempt CPU or records / total attempted

  recovery latency               fault trigger to resumed useful progress or terminal outcome

  peak RSS                       coordinator, worker control, and task child measured separately

  I/O                            logical bytes, read/write syscalls, page faults or device bytes where available
  ------------------------------------------------------------------------------------------------------------------------

## 231. Latency Methodology

- Define start and end events precisely for submission, assignment, task, staging, verification, commit, and run completion.
- Use monotonic clocks within a process. Cross-process spans use event correlation and avoid sub-microsecond claims without clock synchronization.
- Report median, p90, p95, p99, maximum, and sample count for task-level distributions.
- Do not mix first-run cold start with steady-state without labeling.
- Keep failed, retried, and duplicate attempts in separate distributions.
- Publish histograms or empirical distributions when tails matter; one average hides lease and I/O stalls.

## 232. Throughput Methodology

- Report both logical committed records and total attempted records.
- Exclude dataset generation unless the study is explicitly end-to-end provisioning.
- State whether file data is cold, warm in page cache, or uncontrolled.
- Run enough records that timer resolution and startup overhead do not dominate, or report startup separately.
- Verify final digest on every measured run or at least every sample according to benchmark policy; never disable correctness silently for speed.
- Record coordinator and worker CPU so a throughput gain from oversubscription or hidden threads is visible.

## 233. Scaling Study

1.  Choose a dataset large enough that one worker runs for a meaningful interval.
2.  Pin or record worker placement and ensure C++ internal threads are one unless studying nested parallelism.
3.  Run 1, 2, 4, and 8 workers in randomized order across repetitions.
4.  Collect run wall time, worker CPU, coordinator CPU, peak memory, I/O, task durations, and queue depths.
5.  Calculate speedup and parallel efficiency with uncertainty intervals.
6.  Explain divergence from linear scaling using measured coordinator, storage, memory-bandwidth, page-cache, or partition imbalance evidence.
7.  Repeat with at least two partition sizes to separate scheduling overhead from resource contention.

## 234. Partition Size Study

**Table 77 --- Partition-size tradeoffs to measure.**

  -------------------------------------------------------------------------------------------------
  Measure                       Expected small-partition effect   Expected large-partition effect
  ----------------------------- --------------------------------- ---------------------------------
  tasks/second                  high required rate                low required rate

  coordinator CPU               higher                            lower

  load balance                  better                            worse under skew

  retry lost work               smaller                           larger

  cancellation responsiveness   better at boundaries              coarser unless batch checks

  result files/merge overhead   more                              fewer

  peak per-task state           lower                             potentially higher
  -------------------------------------------------------------------------------------------------

## 235. Serialization and Transport Study

- Measure encode time, decode time, frame bytes, syscalls, and queue wait separately.
- Use the same typed message sequence and payload content for embedded, UDS, and TCP variants.
- Test payload sizes representative of control messages rather than transferring dataset blobs artificially.
- For large inline payload experiment, state that it violates normal control/data-plane separation and treat it as a contrast.
- Measure backpressure by slowing the receiver and observing bounded memory and sender wait.
- A lower microbenchmark latency does not imply lower run time if protocol is not the bottleneck.

## 236. C++ Boundary Study

- Measure pure function call overhead with empty or tiny buffers.
- Sweep batch sizes and record Python allocation, C++ compute, result conversion, and total time.
- Compare Python reference, NumPy candidate if used, and C++ under the same logical work.
- Run dense and sparse grouping distributions.
- Report CPU cycles or instructions per record from perf when stable.
- Verify every sample result or a deterministic subset and record failures.
- Explain the crossover point below which the extension is not beneficial.

## 237. Shared-Memory Study

The shared-memory experiment must compare against a bounded file/queue baseline and include engineering cost, not only throughput.

- Measure producer copy time, consumer wait, cache misses, context switches, and end-to-end task time.
- Sweep slot size and slot count.
- Test full-buffer backpressure, producer crash, consumer crash, and shutdown wakeup.
- Include a correctness digest and no-overwrite invariant.
- Report whether shared memory improves the actual run or only a microbenchmark.
- Document complexity and portability cost even when faster.

## 238. Coordinator Capacity Study

- Use no-op or tiny tasks to find maximum sustainable lease/commit rate.
- Measure coordinator CPU, database write time, event-loop lag, ready-window queries, and output queue.
- Sweep worker count and task completion burstiness.
- Compare heartbeat rates and optional durable-heartbeat batching.
- Find the saturation point and show backpressure rather than driving the process into unbounded lag.
- This is a capacity result for the test machine and configuration, not a production guarantee.

## 239. Failure and Recovery Study

**Table 78 --- Failure-performance experiments.**

  ----------------------------------------------------------------------------------------------------------------
  Experiment                            Primary measurements
  ------------------------------------- --------------------------------------------------------------------------
  worker kill during task               detection, lease expiry, retry issue, useful progress resumed, lost work

  coordinator kill after lease commit   restart duration, lease reconciliation, duplicate/lost work

  coordinator kill after task commit    restart duration, idempotent finish resolution

  slow artifact verification            queue depth, commit latency, control-plane lag

  disk full during stage                failure detection, cleanup, retry decision

  network partition simulation          renewal failure, stale result rejection, recovery after reconnect
  ----------------------------------------------------------------------------------------------------------------

## 240. Memory Measurement

- Report coordinator, worker control, and child peak RSS separately.
- Measure memory as dataset and task count scale, not only one run.
- Distinguish mapped virtual memory from resident pages.
- Record queue capacity and observed high-water mark.
- Use heap/allocation profiles to explain C++ and Python object costs.
- A page cache is system memory outside process RSS; discuss it when file workloads are warm.

## 241. Warm-Up and Cache Policy

**Table 79 --- Warm-up and cache-study modes.**

  -----------------------------------------------------------------------------------------------------------------------
  Policy                         Use
  ------------------------------ ----------------------------------------------------------------------------------------
  cold process                   Include import, extension load, database open, and startup; useful for CLI experience.

  warm process                   Coordinator/workers already running; isolate steady execution.

  cold page cache                Requires privileged or large-data methods; difficult and must be documented.

  warm page cache                Repeat same dataset; useful for compute focus.

  mixed/uncontrolled cache       Acceptable for development only; not a strong publication claim.
  -----------------------------------------------------------------------------------------------------------------------

## 242. Statistical Analysis

- Retain all valid samples and mark exclusions with reasons before examining preferred outcome when possible.
- Use median and robust spread for skewed timings; include arithmetic mean where informative.
- Bootstrap confidence intervals or report quantiles and sample count rather than implying precision from one run.
- Compare paired or interleaved samples when variants run under the same drift conditions.
- Do not report more significant digits than measurement variability supports.
- A statistically detectable difference may still be operationally irrelevant; report effect size.

## 243. Raw Benchmark Record Schema

    {
      "schema": "forge.benchmark_sample.v1",
      "study_id": "scaling-filtered-stats-v1",
      "sample_id": "...",
      "variant": "cpp-unix-4workers",
      "workload_manifest_sha256": "...",
      "source_commit": "...",
      "environment_sha256": "...",
      "repetition": 7,
      "valid": true,
      "invalid_reason": null,
      "metrics": {
        "run_wall_ns": 1234567890,
        "records_committed": 100000000,
        "records_attempted": 100000000,
        "coordinator_cpu_ns": 81200000,
        "worker_cpu_ns": 4100000000,
        "peak_rss_bytes": 734003200
      }
    }

## 244. Profiling Toolkit

**Table 80 --- Profiling tools and questions.**

  ---------------------------------------------------------------------------------------------------
  Tool                            Question
  ------------------------------- -------------------------------------------------------------------
  cProfile/py-spy                 Where does Python coordinator or worker time go?

  Linux perf stat                 Cycles, instructions, branches, misses, faults, context switches.

  Linux perf record/report        Which native/Python symbols consume CPU?

  strace -c or targeted tracing   Which syscalls and I/O patterns dominate?

  flame graph                     How do call stacks contribute over time?

  tracemalloc                     Which Python allocations grow?

  heaptrack/massif as available   Where does native heap usage occur?

  SQLite EXPLAIN QUERY PLAN       Are scheduler and status queries indexed?

  compiler optimization reports   Was vectorization or inlining applied?
  ---------------------------------------------------------------------------------------------------

## 245. Optimization Ladder

1.  Reproduce the performance problem with a frozen workload and baseline tag.
2.  Profile and state a falsifiable bottleneck hypothesis.
3.  Choose the smallest change that tests the hypothesis.
4.  Add or strengthen correctness tests around the affected boundary.
5.  Run microbenchmark and end-to-end benchmark; a local gain may not improve the run.
6.  Inspect CPU, memory, I/O, and tail effects for regressions.
7.  Record before/after raw data and update the ADR or experiment note.
8.  Keep, revise, or revert the change based on evidence.
9.  Re-profile because the bottleneck may have moved.

## 246. Candidate Optimization Experiments

**Table 81 --- Candidate performance experiments.**

  ---------------------------------------------------------------------------------------------------------------------------------------------------
  Experiment                    Hypothesis                                        Required proof
  ----------------------------- ------------------------------------------------- -------------------------------------------------------------------
  Batch heartbeat writes        SQLite write rate limits coordinator              same lease safety; lower DB time and event-loop lag

  Ready-task window/cache       Repeated SQL selection dominates                  bounded memory; no starvation; query time reduction

  Dense C++ accumulator         Hash allocation dominates dense stream workload   same results; lower cycles and allocations

  mmap reader                   Read copies/syscalls dominate                     same validation; better end-to-end result under named cache mode

  Compact result arrays         Python object construction dominates              same public schema or converter; lower time/memory

  MessagePack control payload   JSON encode/decode limits no-op task rate         protocol parity; measurable run/capacity gain

  Shared-memory batches         IPC copies dominate local pipeline                bounded correctness; meaningful end-to-end improvement

  Hierarchical merge            Single merge scales poorly with many partitions   same canonical result; failure semantics and complexity justified
  ---------------------------------------------------------------------------------------------------------------------------------------------------

## 247. Negative Results Policy

A credible engineering study includes changes that did not help. Document the hypothesis, implementation, result, and explanation. Examples may include mmap being slower on a cold-cache workload, MessagePack saving bytes but not run time, or a custom allocator adding complexity without measurable gain.

- Keep negative experiment notes even if the code is reverted.
- Do not cherry-pick only favorable samples.
- Explain whether the result falsified the hypothesis or whether the experiment was inconclusive.
- State what would cause the decision to be revisited.
- Negative results are strong interview material when the reasoning is clear.

## 248. Performance Claim Rules

- Name the workload, hardware, worker count, build, integrity, durability, and cache mode.
- Use achieved X on this setup rather than can handle X in production.
- State whether throughput counts logical committed records or all attempted records.
- Do not call a system linearly scalable when efficiency falls materially; show the curve.
- Do not call an implementation zero-copy unless every relevant ownership transfer and copy is demonstrated.
- Do not call it low latency; report measured distributions and scope.
- Do not generalize a C++ speedup from one kernel to all Python workloads.
- Link headline numbers to raw evidence and a tagged release.

## 249. Benchmark Report Structure

1.  Question and hypothesis.
2.  System and variant description.
3.  Frozen workload and correctness validation.
4.  Environment and controls.
5.  Raw sample summary and exclusions.
6.  Results with variability and plots.
7.  Profile evidence.
8.  Interpretation and bottleneck explanation.
9.  Limitations and threats to validity.
10. Decision, next experiment, and reproducibility commands.

## 250. Benchmark Acceptance Gate

- Every plot regenerates from immutable raw records.
- Every sample points to workload, environment, build, and correctness result.
- At least one no-op overhead, scaling, partition-size, C++ boundary, and recovery study is complete.
- Results include variability and invalid-sample accounting.
- Profile evidence supports each optimization narrative.
- Negative or neutral results are retained.
- Public claims are scoped and reproducible from a tagged release.
