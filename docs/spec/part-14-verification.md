# Part XIV - Verification, Testing, Fuzzing, and Correctness Evidence

## 203. Verification Philosophy

Forge cannot be validated by one end-to-end demo. Distributed bugs often hide in uncommon event orderings, uncertain outcomes, malformed boundaries, and restart states. The verification strategy therefore combines independent reference execution, pure transition tests, database constraints, generated state-machine sequences, process-level integration, crash-point recovery, protocol fuzzing, C++ sanitizers, and benchmark regression.

Tests should prove both safety and liveness within the stated model. Safety asks whether an invalid result or state can become visible. Liveness asks whether eligible work eventually resumes when healthy capacity exists and policies permit. A test that only waits for success without inspecting attempt history can miss duplicate commits, leaked children, or unbounded retries.

## 204. Evidence Layers

**Table 69 --- Verification evidence layers.**

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Layer                          Primary question                                                                             Typical tools
  ------------------------------ -------------------------------------------------------------------------------------------- ---------------------------------------------------
  Static checks                  Are obvious type, import, style, and unsafe-code issues caught before execution?             mypy/pyright, Ruff, compiler warnings, clang-tidy

  Pure unit tests                Do value objects, planners, canonicalizers, and transition functions obey their contracts?   pytest, GoogleTest

  Schema and fixture tests       Are encoded formats stable and malformed inputs rejected?                                    golden files, binary fixtures

  Property/state-machine tests   Do invariants hold over generated sequences and values?                                      Hypothesis or custom generator

  Differential tests             Do independent implementations produce equivalent results?                                   Python reference versus C++ and distributed paths

  Integration tests              Do real processes, sockets, database, and artifacts work together?                           pytest subprocess fixtures

  Crash/recovery tests           Does state remain valid at uncertain transaction and artifact boundaries?                    fault injector, kill/restart harness

  Fuzz and sanitizer tests       Do decoders and native code survive hostile bytes and undefined behavior checks?             libFuzzer/AFL-style harness, ASan, UBSan

  Performance regression         Did a change materially alter cost under a frozen workload?                                  benchmark runner and threshold policy

  Manual technical review        Can a human understand the guarantee, tradeoff, and evidence?                                ADR, design review, demo rehearsal
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 205. Test Repository Structure

    tests/
      unit/
        domain/
        planner/
        scheduler/
        canonicalization/
      schema/
        datasets/
        manifests/
        protocol/
        results/
      property/
        state_machines/
        partitioning/
        canonical_results/
      differential/
        python_vs_cpp/
        reference_vs_cluster/
      integration/
        local_cluster/
        sockets/
        cancellation/
      recovery/
        crash_points/
        database/
        artifacts/
      chaos/
      performance/
      fixtures/
      support/
        fake_clock.py
        process_harness.py
        fault_injector.py
        temp_cluster.py

## 206. Unit Test Inventory

**Table 70 --- Core unit-test inventory.**

  --------------------------------------------------------------------------------------------------------------------
  Area                           Cases
  ------------------------------ -------------------------------------------------------------------------------------
  IDs and value types            parse, equality, canonical form, invalid length, serialization round-trip

  Manifest validation            missing/unknown fields, type bounds, cross-field conflicts, canonical hash

  Dataset header                 endianness, short input, bad magic/version, overflow, file-size mismatch

  Partition planner              coverage, no overlap, exact multiples, final short partition, multi-file boundaries

  Kernel registry                exact version, unknown implementation, parameter model, capability advertisement

  Run transitions                every legal transition and every forbidden transition

  Task/attempt transitions       lease, start, expiry, retry, stage, commit, cancel, terminal states

  Retry classifier               each error class, budget, backoff, deterministic repeated failure

  Scheduler policy               eligibility, fairness key, retry time, capability filters

  Canonical digest               map order, paths, IDs, timing exclusion, stable numeric encoding

  Artifact resolver              root confinement, collision, symlink, file type, unique names

  Protocol decoder               fragmentation, concatenation, bounds, versions, flags, CRC

  Configuration                  precedence, unknown keys, path base, redaction, invalid ranges

  CLI rendering                  JSON schema, exit codes, no secret leakage
  --------------------------------------------------------------------------------------------------------------------

## 207. Table-Driven State Transition Tests

    @pytest.mark.parametrize(
        ("initial", "event", "expected"),
        [
            (TaskState.PENDING, LeaseIssued(gen=1), TaskState.LEASED),
            (TaskState.LEASED, StartAcknowledged(gen=1), TaskState.RUNNING),
            (TaskState.RUNNING, ResultStaged(gen=1), TaskState.STAGED),
            (TaskState.STAGED, CommitAccepted(gen=1), TaskState.COMMITTED),
            (TaskState.RUNNING, LeaseExpired(gen=1), TaskState.PENDING),
            (TaskState.PENDING, RunCancelled(), TaskState.CANCELLED),
        ],
    )
    def test_task_transitions(initial, event, expected):
        assert reduce_task(initial, event).state is expected

Create a complementary invalid-transition table and assert stable error codes. A transition reducer should not inspect sockets or database state; the repository method supplies the preconditions and persists the result transactionally.

## 208. State-Machine Property Testing

A generated model can create runs, workers, tasks, leases, heartbeats, expiries, failures, completions, cancellations, and restarts. After every command, compare the system-under-test snapshot against a simpler in-memory model and assert invariants.

- Commands have preconditions so generated sequences remain meaningful while still exploring races and repetitions.
- The model deliberately represents task and attempt separately and uses one simple committed-winner rule.
- Include duplicate and stale messages, not only legal current messages.
- Shrink failing sequences and print the seed plus minimized command trace.
- Persist regression traces as human-readable fixtures after fixing a bug.
- Run a small state-machine budget on every pull request and a larger seed corpus nightly.

## 209. Planner Property Tests

- Sum of partition record_count equals declared dataset records.
- Sorted partitions begin at zero or file start and have no gaps or overlap.
- Every boundary maps to a valid byte range using checked arithmetic.
- Same inputs yield identical descriptors and plan digest.
- Changing only target partition size does not change dataset identity or record order.
- Each partition seed is stable and distinct enough for the selected derivation function.
- Reference concatenation of partition records equals the original logical dataset sequence.

## 210. Differential Testing

Differential tests compare implementations that should share semantics but not implementation details.

**Table 71 --- Differential test pairs.**

  --------------------------------------------------------------------------------------------------------------------------------------------------------------
  Comparison                                          Inputs                                            Comparison output
  --------------------------------------------------- ------------------------------------------------- --------------------------------------------------------
  Python record decoder vs C++ decoder                Generated valid and malformed buffers             records/errors and context

  Python stats vs C++ stats                           Generated events, masks, boundaries               canonical group result and digest

  Reference single-process vs embedded multiprocess   Frozen run manifests                              final canonical result

  Embedded queue vs Unix socket transport             Same manifest and fault-free seed                 task plan, logical result, allowed attempt differences

  Fresh run vs crash/restart run                      Same manifest plus deterministic fault schedule   final result and postconditions

  Buffered read vs mmap                               Same partitions                                   logical result and bytes/records counters
  --------------------------------------------------------------------------------------------------------------------------------------------------------------

## 211. Failure Shrinking

- Reduce event count while preserving failure.
- Reduce number of workers, runs, tasks, and retries.
- Remove unrelated messages or faults from the command trace.
- Shrink partition boundaries and event values.
- Record exact software commit, seed, and fault occurrence index.
- Emit a standalone reproduction manifest or pytest case when practical.
- A minimized failure becomes a permanent regression fixture, not only an issue description.

## 212. Protocol Fuzzing

- Fuzz the fixed-header parser independently from payload decoding.
- Fuzz incremental fragmentation: arbitrary chunk boundaries and empty reads.
- Mutate length, version, flags, sequence, CRC, and nested collection counts.
- Seed with every valid message type and known malformed regression fixture.
- Assert bounded memory, bounded processing time, no uncaught crash, and one of a small valid decoder outcomes.
- Run native decoder fuzz targets under ASan/UBSan if any parsing is in C++.
- Persist corpus files with short names and a manifest explaining the bug class.

## 213. C++ Native Test Plan

- Endian helpers at minimum, maximum, signed boundary, and unaligned input.
- Record parser for empty, exact, short, extra-byte, and very large declared counts.
- Aggregation for one group, many groups, no selected records, negative values, overflow, and sorted output.
- Result equivalence across batch splits: one whole buffer versus every possible two-way split.
- Exception safety and no leak when allocation or validation fails mid-operation.
- Build-info and API-version compatibility.
- Debug assertions and release behavior both tested where contracts differ.

## 214. Process Integration Harness

A reusable test harness should start coordinator and workers in isolated temporary directories, choose free endpoints, stream logs, enforce timeouts, kill named processes, and verify no children or sockets remain afterward.

- Use process groups or pidfds so cleanup is reliable.
- Wait for readiness through a supported signal, not arbitrary sleep.
- Capture stdout/stderr and structured logs into test artifacts on failure.
- Provide methods to pause, resume, terminate, kill, disconnect, fill disk quota fixture, and trigger named fault points.
- Every integration test has a hard wall-clock timeout and post-test invariant scan.
- Random ports or socket names are unique per test worker to support parallel CI safely.

## 215. End-to-End Integration Cases

**Table 72 --- End-to-end integration tests.**

  -----------------------------------------------------------------------------------------------------------------------
  Test ID                        End-to-end case
  ------------------------------ ----------------------------------------------------------------------------------------
  INT-001                        One worker, Python kernel, successful run.

  INT-002                        Four workers, Python kernel, same result as reference.

  INT-003                        Four workers, C++ kernel, same result as Python reference.

  INT-004                        Worker crash during read; task retries elsewhere.

  INT-005                        Worker crash after staged write; no partial commit.

  INT-006                        Coordinator crash after lease transaction; recovery requeues safely.

  INT-007                        Coordinator crash after task commit; duplicate finish is idempotent.

  INT-008                        Cancel while tasks run; no later commit.

  INT-009                        Two attempts race to finish; one winner.

  INT-010                        Malformed peer is disconnected without affecting healthy run.

  INT-011                        Slow result verification applies bounded backpressure.

  INT-012                        Restart during MERGING finishes exactly once.

  INT-013                        Missing committed artifact prevents readiness.

  INT-014                        Diagnostic bundle reconstructs the injected failure.

  INT-015                        Local cluster leaves no processes, socket files, or open staging paths after shutdown.
  -----------------------------------------------------------------------------------------------------------------------

## 216. Crash-Recovery Test Method

1.  Create a small deterministic run whose correct result is already known.
2.  Arm one named fault at a specific occurrence and entity.
3.  Launch real coordinator and worker processes.
4.  Wait for fault evidence or process termination without relying on a fixed sleep.
5.  Restart the killed component or entire cluster with the same durable directories.
6.  Wait for terminal run outcome or expected fail-closed state.
7.  Run full metadata and artifact invariant scan.
8.  Compare final logical result with reference when recovery should succeed.
9.  Record attempt history and ensure no forbidden commit, leaked lease, or orphan beyond policy.

## 217. Concurrency and Race Testing

- Use barriers at commit, cancel, expiry, and duplicate-finish boundaries to force both transaction orders.
- Run many clients with the same idempotency key.
- Run several workers requesting the final pending task simultaneously.
- Delay artifact verification while cancellation or another attempt commits.
- Reconnect a worker while its old session is still closing.
- Stress SQLite busy handling with status readers and task completions.
- Avoid relying only on probabilistic stress; deterministic barriers make regressions reproducible.

## 218. Deterministic Simulation

A simulation executes coordinator domain events without real time or processes. It should model worker speed, message delay, crash, lease timeout, and task duration. The same invariants run after every simulated event.

- Use a priority queue ordered by simulated time and stable event sequence.
- Record a complete event trace and replay it exactly.
- Compare scheduler policies and failure settings quickly over thousands of seeds.
- Do not use simulation throughput as product throughput evidence.
- Use discovered failing traces to construct real integration tests at important boundaries.

## 219. Sanitizer and Dynamic Analysis Matrix

**Table 73 --- Dynamic-analysis tool matrix.**

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------
  Tool                         Target                                                    Cadence                     Notes
  ---------------------------- --------------------------------------------------------- --------------------------- ----------------------------------------------
  AddressSanitizer             C++ tests and extension integration                       Every PR or dedicated job   Detect memory errors; do not benchmark.

  UndefinedBehaviorSanitizer   C++ tests and extension                                   Every PR                    Include signed overflow policy tests.

  ThreadSanitizer              Only if C++ threads or native shared-memory concurrency   Nightly/targeted            May conflict with other tooling.

  Valgrind/Memcheck            Selected native paths                                     Pre-release                 Slow; useful second signal.

  Python tracemalloc           Coordinator/worker allocation studies                     Targeted                    Not a complete native-memory view.

  faulthandler                 Python process crash/hang diagnostics                     Enabled in tests            Capture stacks on timeout.

  coverage.py/llvm-cov         Python/C++ coverage                                       CI report                   Coverage guides gaps; it is not correctness.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------

## 220. Performance Regression Policy

Performance tests are noisy and should not make every pull request flaky. Use small smoke thresholds in CI and run controlled studies on a stable machine for publication.

- CI rejects catastrophic regressions such as more than a broad threshold on no-op scheduler throughput or parser benchmark.
- A stable dedicated environment produces trend data for tighter thresholds.
- Correctness changes may intentionally cost performance; document and approve the tradeoff.
- Raw samples and environment fingerprints accompany any regression claim.
- Never compare sanitizer, debug, different durability, or different integrity modes as if equivalent.

## 221. Coverage and Mutation Testing

- Track branch coverage for state transitions, error classifiers, decoder bounds, and recovery code.
- Require tests for every stable error code and terminal state.
- Use mutation testing selectively on pure transition and canonicalization modules to detect weak assertions.
- Do not chase 100% line coverage in trivial accessors while failure boundaries remain untested.
- Publish a coverage summary but pair it with the scenario matrix and invariant evidence.

## 222. Flaky Test Policy

- A flaky test is a defect, not an expected property of distributed systems.
- Quarantine only with an issue, owner, failure evidence, and deadline; do not silently rerun until green.
- Use fake clocks and readiness signals instead of sleeps.
- Capture process trees, ports, queue depths, and last state events on timeout.
- Randomized tests print seeds and preserve minimized failures.
- CI reports test duration trends so accidental long waits are visible.

## 223. Verification Release Gate

- All P0/P1 scenario IDs map to automated tests or explicitly documented manual evidence.
- Independent Python reference and C++ differential corpus are green.
- State-machine and crash-point tests preserve every core invariant.
- Protocol fuzz corpus runs clean under selected sanitizers.
- No leaked processes, open sockets, or staging paths remain after integration suites.
- Coverage gaps in commit, cancellation, lease, recovery, or path safety are resolved or called out.
- A clean environment can run the complete documented test commands.
