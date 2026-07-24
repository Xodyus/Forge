# Part I - Product Definition and Acceptance Contract

## 1. Project Thesis

Forge will be a deterministic, local-first event-replay and compute engine written primarily in Python, with a modern C++20 extension for performance-critical parsing and aggregation. A client defines an immutable dataset and an experiment. The coordinator converts the experiment into deterministic partitions and tasks, leases those tasks to workers, accepts staged outputs, and makes one result per task visible through a conditional commit. Workers may crash or execute the same task more than once, but completed runs remain reproducible and committed outputs remain unambiguous.

The project is not judged by the number of distributed-systems terms in its README. It is judged by whether another engineer can answer five concrete questions from code and evidence.

- **Is the execution contract precise?** The repository defines what a dataset, run, task, attempt, lease, retry, checkpoint, commit, cancellation, and result mean.
- **Is failure engineered?** Worker crashes, coordinator restarts, expired leases, duplicate completions, malformed messages, disk errors, and partial artifacts have explicit outcomes.
- **Is the implementation understandable?** Control and data planes are separated, ownership is documented, state transitions are visible, and the simple baseline remains available.
- **Is performance measured?** Scaling, serialization, C++ boundary costs, scheduler overhead, memory, and recovery time are measured under frozen workloads with raw results.
- **Are claims honest?** The project distinguishes implemented, experimental, deferred, and out-of-scope capabilities. The resume never implies production guarantees that the repository does not provide.

Forge should be released as a sequence of independently credible milestones. Gate A can be impressive without multi-host execution. Gate B can be impressive without shared memory. Gate C is a performance and failure study built on top of a system that was already correct.

## 2. Outcome Ladder

**Table 3 --- Forge outcome ladder.**

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Level                                      Acceptance description
  ------------------------------------------ -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Level 1 --- Deterministic reference path   One process loads an immutable dataset, partitions it deterministically, executes a registered Python kernel, merges results, writes a run manifest, and reproduces byte-identical normalized output.

  Level 2 --- Durable local scheduler        A coordinator persists runs and tasks, launches multiple workers, uses bounded queues and leases, retries crashed work, stages attempt outputs, and conditionally commits one result per task.

  Level 3 --- Strong systems project         Workers communicate over a framed Unix-domain or TCP protocol, the coordinator recovers from restart, the C++ extension accelerates a measured bottleneck, observability is complete, and failure injection is automated.

  Level 4 --- Standout engineering study     The repository compares transport or storage alternatives, publishes scaling and recovery experiments, documents negative results, demonstrates multi-host or shared-memory extensions only where justified, and presents an evidence-backed technical narrative.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 3. Primary Goals

- Define a deterministic execution model for immutable event streams and trusted user-defined computation.
- Demonstrate Python systems engineering: asyncio, multiprocessing, process lifecycle, signals, serialization, bounded queues, type checking, testing, and packaging.
- Demonstrate modern C++20 engineering through a narrow, batch-oriented extension with explicit ownership, buffer handling, error translation, profiling, and sanitizer coverage.
- Demonstrate distributed-systems reasoning: leases, fencing tokens, idempotency, at-least-once execution, exactly-once visible publication, durable metadata, restart recovery, and fault injection.
- Separate the control plane from large data movement so scheduler messages remain small and understandable.
- Measure where time and memory are spent instead of assuming that networking, Python, or serialization is the bottleneck.
- Create a repository that a reviewer can build, test, run, intentionally break, recover, benchmark, and discuss within a reasonable amount of time.
- Produce truthful resume bullets and interview stories whose numbers and guarantees can be regenerated from a tagged release.

## 4. Explicit Non-Goals

Forge will not attempt to become a general-purpose production scheduler. The following are outside the first public release unless a later experiment explicitly isolates them:

- Executing untrusted or adversarial user code. Python kernels run with the worker process privileges and must be treated as trusted.
- A general directed-acyclic-graph engine comparable to Spark, Ray, Dask, Airflow, or a Kubernetes scheduler.
- Dynamic cluster autoscaling, cloud billing integration, heterogeneous accelerator scheduling, or fleet management.
- Byzantine fault tolerance, multi-leader consensus, active-active coordinators, or cross-region disaster recovery.
- Exactly-once physical execution. Retries may execute a task more than once; the guarantee concerns result visibility and commit state.
- Arbitrary object serialization across machines. The public contract favors manifests, primitive metadata, immutable files, and registered function identifiers.
- Security certification, public Internet exposure, multi-tenant isolation, or storage of secrets and regulated data.
- A claim that the C++ path is always faster. The extension is accepted only when controlled measurements show a useful improvement for a defined workload.
- A polished web dashboard before the CLI, logs, metrics, and recovery behavior are complete.
- Recreating a proprietary trading or research platform. The event data and workloads are synthetic or openly licensed and domain-neutral.

Writing down non-goals is part of the project. It demonstrates that the developer can preserve a learning objective under scope pressure.

## 5. Intended Users and Reviewers

**Table 4 --- User and reviewer personas.**

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Persona                    Primary need                                                                                                               Success signal
  -------------------------- -------------------------------------------------------------------------------------------------------------------------- -----------------------------------------------------------------------------------------------------------------
  Experiment author          Describe a dataset, registered function, parameters, seed, and desired worker count without managing processes manually.   The same manifest produces the same logical result in reference and distributed modes.

  Systems developer          Trace a task through validation, partitioning, lease, execution, staging, commit, and recovery.                            State transitions and ownership are explicit in code and documentation.

  Performance investigator   Run frozen workloads, capture raw metrics, compare implementations, and identify bottlenecks.                              Every published chart is generated from versioned raw data and environment metadata.

  Failure investigator       Inject crashes, timeouts, malformed messages, or artifact corruption and understand the resulting state.                   The system either recovers according to contract or fails loudly without silently publishing an invalid result.

  Hiring reviewer            Assess programming depth, systems knowledge, testing discipline, communication, and honesty quickly.                       The repository provides a coherent evidence path instead of a large code dump.

  Lucas                      Use the project for learning, portfolio evidence, and interview preparation.                                               He can explain the design from first principles and reproduce every resume claim.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 6. Representative End-to-End Use Cases

- Generate a deterministic 100-million-record synthetic telemetry dataset with a versioned manifest and checksums.
- Run a pure-Python aggregation in one process and record a canonical reference result.
- Submit the same experiment to a four-worker local cluster and obtain a result with the same normalized digest.
- Kill one worker halfway through a partition; allow its lease to expire; retry the task on another worker; publish one committed result.
- Allow two attempts of the same task to finish after a lease race; commit exactly one attempt and safely discard the loser.
- Terminate the coordinator after several tasks commit; restart it; rebuild in-memory scheduling state; and execute only incomplete work.
- Cancel a run while workers are active; prevent new assignments; request cooperative cancellation; and mark staged-but-uncommitted outputs for cleanup.
- Run the C++ parser/aggregation kernel against the same partitions as the Python reference and compare every result and checksum.
- Use a bounded queue to slow input when result writing cannot keep up, demonstrating backpressure rather than unbounded memory growth.
- Measure 1-, 2-, 4-, and 8-worker scaling, coordinator CPU, memory, serialization cost, C++ boundary overhead, p50/p99 task completion time, and recovery delay.
- Export a diagnostic bundle containing the run manifest, configuration, state transitions, logs, metrics, environment fingerprint, and failing seed.
- Reproduce the public demonstration from a clean checkout using documented commands and no manually edited output.

## 7. Priority Model

**Table 5 --- Requirement priority model.**

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Priority             Meaning                                                       Decision rule
  -------------------- ------------------------------------------------------------- -----------------------------------------------------------------------------------------
  P0                   Required for the correct and durable local-cluster release.   The project is not credible without it; stop optional work until it is complete.

  P1                   Required for the strong systems and portfolio release.        May begin only when dependent P0 invariants and tests are green.

  P2                   Optional differentiator or measured alternative.              Implement only when it adds a clear hiring signal and does not threaten a release gate.

  Research             Experiment whose outcome is uncertain by design.              Preserve the baseline, define a hypothesis, and publish negative results honestly.
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 8. Functional Requirements

**Table 6 --- Functional requirements.**

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ID              Area                         Acceptance statement                                                                                                                Priority
  --------------- ---------------------------- ----------------------------------------------------------------------------------------------------------------------------------- ---------------
  FR-001          Dataset registration         Register an immutable dataset manifest containing format version, files, sizes, record counts, checksums, and schema identity.      P0

  FR-002          Experiment submission        Submit a validated experiment manifest and receive a durable run ID before execution begins.                                        P0

  FR-003          Deterministic planning       Generate the same ordered partition plan for the same dataset, partition policy, and manifest version.                              P0

  FR-004          Reference execution          Execute every partition in a single process using the same function contract as distributed mode.                                   P0

  FR-005          Worker registration          Register worker identity, protocol version, process identity, capabilities, resource limits, and last heartbeat.                    P0

  FR-006          Pull-based leasing           Allow an eligible worker to request work and receive one bounded lease with task, attempt, and fencing identifiers.                 P0

  FR-007          Heartbeat renewal            Renew an active lease only when the worker, attempt, and fencing token match current durable state.                                 P0

  FR-008          Attempt staging              Write output to an attempt-specific staging location and report its size and digest without making it visible as the task result.   P0

  FR-009          Conditional commit           Atomically select at most one staged attempt as the committed task result.                                                          P0

  FR-010          Duplicate completion         Reject or discard a losing attempt without changing the already committed result.                                                   P0

  FR-011          Retry                        Create a new attempt after a retryable failure or expired lease while preserving prior attempt history.                             P0

  FR-012          Run completion               Mark a run successful only after all required tasks are committed and the final merge result is verified.                           P0

  FR-013          Run cancellation             Stop new leases, signal active attempts, record cancellation, and prevent later output from being committed.                        P0

  FR-014          Coordinator restart          Reload active runs, reconcile leases and artifacts, and resume incomplete work after process restart.                               P0

  FR-015          Canonical result digest      Produce a stable logical digest independent of worker count, attempt IDs, timestamps, and output path.                              P0

  FR-016          Registered kernels           Select trusted Python or C++ kernels by versioned identifier instead of transferring arbitrary executable objects.                  P0

  FR-017          Bounded queues               Bound work requests, control messages, staged outputs, and in-process batches with visible saturation behavior.                     P0

  FR-018          Status inspection            Query run, task, attempt, worker, lease, progress, failure, and artifact state through CLI and Python API.                          P0

  FR-019          Structured logs              Emit machine-readable events carrying run, task, attempt, worker, and correlation identifiers.                                      P0

  FR-020          Metrics export               Expose counters, gauges, histograms, and timing summaries needed by the benchmark and recovery reports.                             P1

  FR-021          Framed transport             Communicate over an incremental, versioned, length-prefixed protocol that handles partial reads and writes.                         P1

  FR-022          Unix-domain deployment       Run coordinator and independent workers over Unix-domain sockets without in-memory object sharing.                                  P1

  FR-023          TCP deployment               Run workers over loopback or a trusted private network using the same message semantics.                                            P1

  FR-024          C++ acceleration             Execute a batch-oriented C++ parser or aggregation kernel through pybind11 and verify equivalence to Python.                        P1

  FR-025          Checkpoint export            Persist a run checkpoint manifest containing committed-task frontier, merge state, and artifact references.                         P1

  FR-026          Diagnostic bundle            Export all non-secret material needed to reproduce or investigate a run.                                                            P1

  FR-027          Fault injection              Inject named worker, coordinator, transport, and storage failures under deterministic test control.                                 P1

  FR-028          Benchmark runner             Execute versioned workload matrices and write raw records plus environment metadata.                                                P1

  FR-029          Multi-host mode              Support workers on another trusted host with explicit shared-storage assumptions.                                                   P2

  FR-030          Shared-memory data path      Compare a bounded shared-memory batch path against the file/queue baseline.                                                         Research

  FR-031          Speculative execution        Launch a duplicate attempt for a measured straggler while preserving conditional commit semantics.                                  Research

  FR-032          Alternative metadata store   Demonstrate the storage interface with a second transactional backend only if justified.                                            Research
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 9. Nonfunctional Requirements

**Table 7 --- Nonfunctional requirements.**

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  ID                   Quality                   Acceptance statement
  -------------------- ------------------------- -------------------------------------------------------------------------------------------------------------------------------------
  NFR-001              Correctness               No run may be marked successful unless every required task has one valid committed result and the final digest verifies.

  NFR-002              Determinism               A frozen manifest and software version must yield the same canonical result across repeated executions and supported worker counts.

  NFR-003              Durability                Committed task metadata and artifact references survive coordinator restart according to the selected durability mode.

  NFR-004              Bounded memory            Every queue and batch has a configured bound; overload causes backpressure or rejection rather than silent unbounded growth.

  NFR-005              Observability             Every state transition relevant to correctness is reconstructable from durable state and structured events.

  NFR-006              Testability               Time, process termination, message delivery, storage faults, and randomness can be controlled or abstracted in tests.

  NFR-007              Portability               The primary development target is Linux x86-64; unsupported platforms are detected and documented rather than partially working.

  NFR-008              Maintainability           Modules have explicit responsibilities, narrow interfaces, typed models, and no hidden dependency on global mutable state.

  NFR-009              Performance honesty       Published results disclose workload, hardware, software versions, warm-up, repetitions, and known limitations.

  NFR-010              Security posture          The default deployment binds locally, rejects oversized frames and unsafe paths, and clearly states that kernels are trusted.

  NFR-011              Reproducibility           A tagged release includes dependency locks, build instructions, workload seed, raw data, and analysis scripts.

  NFR-012              Reviewability             A new engineer can build, test, run, fail, recover, and benchmark the project from documented commands.

  NFR-013              Resource accountability   Per-run and per-task CPU time, wall time, bytes read/written, retries, and peak memory are recorded where practical.

  NFR-014              Compatibility             Protocol, manifest, dataset, result, and metadata schemas are versioned with defined rejection or migration behavior.

  NFR-015              Graceful shutdown         Normal shutdown stops admission, drains or cancels work according to policy, persists state, and leaves restartable metadata.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 10. Release Gates

### Gate A --- Deterministic Durable Local Cluster

- All P0 requirements are implemented or narrowed by an explicit approved scope decision.
- The Python reference path and local multi-worker path produce the same canonical result across a documented seed corpus.
- Task, attempt, lease, run, and worker state-machine tests are green.
- A worker crash, lease expiry, duplicate completion, cancellation, and coordinator restart each pass deterministic integration tests.
- The metadata database can be inspected and reconciled; no correctness guarantee depends only on in-memory state.
- Bounded queues and backpressure are visible in tests and metrics.
- Static typing, unit tests, integration tests, linting, and packaging checks are green in CI.
- The README can reproduce one successful run and one recovery scenario from a clean checkout.

### Gate B --- Portfolio-Ready Systems Release

- All P1 requirements are implemented or documented as intentional deferrals with impact analysis.
- The framed socket protocol passes fragmentation, coalescing, malformed-input, oversized-frame, disconnect, and timeout tests.
- The C++ extension builds reproducibly, passes sanitizers, and matches the Python reference over generated workloads.
- Coordinator restart, artifact verification, and checkpoint recovery pass fault-injection suites.
- Structured logs, metrics, status commands, and a diagnostic bundle support a complete incident narrative.
- A benchmark report includes frozen manifests, raw JSON/CSV data, environment fingerprints, plots, and analysis scripts.
- A public release contains no secrets, personal data, unsafe sample configuration, dead-code dumps, or unsupported claims.

### Gate C --- Standout Engineering Study

- At least two architecture or implementation alternatives are compared under the same workload and environment.
- At least three performance changes are tied to profiler evidence and include before/after raw results.
- At least one negative or neutral optimization result is documented with an explanation.
- Failure experiments quantify detection, lease expiry, retry, commit, and recovery time.
- The technical presentation explains a hard bug, a semantic tradeoff, a performance surprise, and a scope decision.
- Resume bullets can be regenerated from the tagged release and do not overstate distributed, production, or exactly-once guarantees.

## 11. Minimum Viable Product

The MVP is deliberately smaller than the final repository. It is a Python package and CLI that generates or registers an immutable fixed-record dataset, creates deterministic contiguous partitions, runs a registered pure-Python aggregation in one process, executes the same partitions across a local multiprocessing worker pool, combines results in partition order, writes a run manifest and task records, and verifies the distributed result against the reference digest.

The MVP does not yet require independent socket-connected workers, coordinator restart, C++, or sophisticated leases. It is complete only when dataset and function contracts are explicit, partitioning is deterministic, errors are surfaced, queues are bounded, generated cases are tested, and the result is reproducible. The MVP is a semantic foundation, not a throwaway prototype.

## 12. Success Rubric

**Table 8 --- Project success rubric.**

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Dimension             Weak                                                         Credible                                                             Strong                                                                                         Standout
  --------------------- ------------------------------------------------------------ -------------------------------------------------------------------- ---------------------------------------------------------------------------------------------- --------------------------------------------------------------------------------------------------------
  Execution semantics   Terms are used loosely; retries and commits are ambiguous.   Task and attempt are distinct; basic retry behavior is documented.   State machines, fencing, visibility, and cancellation are explicit and tested.                 Semantics are model-checked or simulated, failure races are demonstrated, and limitations are precise.

  Python engineering    A script launches processes with global state.               Modules, types, tests, and clean CLI exist.                          Async control plane, bounded queues, packaging, observability, and recovery are disciplined.   The implementation is small, clear, profiled, and supports controlled experimentation.

  C++ integration       C++ is listed but not meaningfully used.                     A function is bound through pybind11.                                Batch API, ownership, GIL, exceptions, sanitizers, and differential tests are correct.         The boundary is measured, alternative layouts are compared, and gains are workload-specific.

  Failure handling      Happy-path only.                                             Worker exceptions produce retries.                                   Crash, expiry, duplicates, restart, cancellation, and corruption have tested outcomes.         Failure detection and recovery latency are measured; chaos results are reproducible.

  Performance method    One throughput number without context.                       Repeated timing on named hardware.                                   Frozen workloads, raw data, profiles, statistics, and scaling efficiency.                      Multiple hypotheses, negative results, bottleneck shifts, and evidence-backed claims.

  Portfolio quality     Large code dump and vague README.                            Build and demo instructions work.                                    Architecture, semantics, evidence, limitations, and resume claims are linked.                  A reviewer can reproduce the technical narrative and challenge the decisions.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 13. Scope-Control Rules

- No multi-host mode before restart recovery is reliable on one host.
- No shared-memory ring before measurements show that serialization or copies materially limit the baseline.
- No speculative execution before leases, fencing, duplicate completion, and conditional commit are correct.
- No general DAG scheduler before a one-stage map plus deterministic merge pipeline is complete and well explained.
- No second metadata backend before the transactional interface and SQLite implementation are stable.
- No web dashboard before the CLI can expose every state needed to debug a run.
- No performance headline before the workload manifest, environment capture, and raw output format are frozen.
- No production, distributed, fault-tolerant, exactly-once, or low-latency label without a precise qualifier.
- Every optional feature must identify the hiring signal it adds, the invariant it risks, and the core work it could delay.
- When forced to choose, prefer correctness evidence over feature count, and prefer a clear postmortem over an unverified optimization.
