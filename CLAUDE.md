# Forge

Forge is a deterministic, local-first event-replay and compute engine written primarily
in Python, with a modern C++20 extension for performance-critical parsing and
aggregation. A client defines an immutable dataset and an experiment. The coordinator
converts the experiment into deterministic partitions and tasks, leases those tasks to
workers, accepts staged outputs, and makes one result per task visible through a
conditional commit. Workers may crash or execute the same task more than once, but
completed runs remain reproducible and committed outputs remain unambiguous.

Forge will not attempt to become a general-purpose production scheduler. Out of scope
for the first public release unless a later experiment explicitly isolates them:
executing untrusted or adversarial user code (kernels run with worker process
privileges and must be treated as trusted); a general DAG engine comparable to Spark,
Ray, Dask, Airflow, or a Kubernetes scheduler; dynamic cluster autoscaling, cloud
billing integration, heterogeneous accelerator scheduling, or fleet management;
Byzantine fault tolerance, multi-leader consensus, active-active coordinators, or
cross-region disaster recovery; exactly-once physical execution (retries may execute a
task more than once — the guarantee concerns result visibility and commit state);
arbitrary object serialization across machines; security certification, public
Internet exposure, multi-tenant isolation, or storage of secrets and regulated data; a
claim that the C++ path is always faster; a polished web dashboard before the CLI,
logs, metrics, and recovery behavior are complete; recreating a proprietary trading or
research platform.

## Hard constraints — do not violate these without an explicit instruction from me

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

## Core invariants (§31)

| ID | Invariant |
|---|---|
| INV-001 | At most one committed attempt exists for a task. |
| INV-002 | A committed task has a committed artifact reference and matching digest. |
| INV-003 | A run is SUCCEEDED only when all required tasks and final merge are committed and verified. |
| INV-004 | A task attempt belongs to exactly one task and one worker lease generation. |
| INV-005 | Fencing generations for a task increase monotonically. |
| INV-006 | A stale generation cannot renew a lease or become committed. |
| INV-007 | A cancelled or terminal run does not create new leases. |
| INV-008 | A partition plan is immutable after the run enters RUNNING. |
| INV-009 | Committed artifact paths are immutable and never reused for different content. |
| INV-010 | Attempt staging paths are unique and cannot overwrite another attempt. |
| INV-011 | Every state transition records a durable reason or source event. |
| INV-012 | Retry count equals the number of created attempts minus the initial attempt, subject to explicit administrative operations. |
| INV-013 | A worker cannot hold more active leases than its accepted capacity. |
| INV-014 | Queue sizes never exceed configured hard bounds. |
| INV-015 | Canonical result digests exclude nondeterministic run metadata. |
| INV-016 | A metadata transaction never points at an unverified or missing committed artifact. |
| INV-017 | A task cannot transition from COMMITTED, FAILED, or CANCELLED back to an executable state. |
| INV-018 | The planner creates complete, non-overlapping coverage of the declared dataset slice. |
| INV-019 | The reference and distributed paths share the manifest and partition contracts but not an implementation that could mask the same bug. |
| INV-020 | All schema and protocol versions are validated before their fields are interpreted. |

## Dependency direction (§40)

```
forge.api / forge.cli
          |
          v
forge.coordinator -----> forge.metadata
      |   |             forge.artifacts
      |   +-----------> forge.protocol / forge.transport
      v
forge.domain <---------- forge.worker
      ^                       |
      |                       v
forge.planner           forge.kernels / forge_cpp
      |
      v
forge.datasets
```

- Domain types and state transitions must not import the coordinator, database, transport, or CLI.
- The coordinator depends on metadata and artifact interfaces, not concrete SQLite paths or directory layouts.
- Workers depend on protocol and kernel interfaces but do not import coordinator internals.
- Benchmark and test packages may depend on public interfaces and controlled test hooks; core packages must not import benchmark code.
- C++ bindings expose domain-neutral batches and result structures. They should not open the metadata database or decide leases.
- Circular imports are a design signal. Resolve them by moving shared value types downward rather than using runtime import tricks.

## Pure core and impure edges (§41)

Keep the hardest semantic decisions in pure or deterministic functions whenever
possible. Examples include transition validation, retry classification, partition
planning, merge ordering, canonicalization, and scheduling eligibility. Keep time,
sockets, processes, files, and SQL behind explicit adapters.

| Pure or deterministic core | Impure edge |
|---|---|
| `validate_run_manifest(manifest, registries)` | Read manifest bytes and resolve artifact URI |
| `plan_partitions(dataset, policy)` | Inspect file metadata or checksum files |
| `next_task_state(state, event)` | Persist transition transaction |
| `eligible_tasks(snapshot, worker_capabilities)` | Receive worker request over socket |
| `retry_decision(error, attempts, policy)` | Schedule timer and send assignment |
| `canonical_result_digest(result)` | Write staged artifact and fsync |
| `recovery_actions(metadata_snapshot, now)` | Open SQLite and inspect filesystem |

## Glossary (§427)

| Term | Definition |
|---|---|
| admission control | Policy that limits which runs or tasks may consume resources before scheduling. |
| artifact | Immutable file or object produced by one attempt or final merge, identified by descriptor and digest. |
| attempt | One physical execution of a logical task. A task may have multiple attempts over time. |
| backpressure | Mechanism that slows or rejects producers when bounded downstream capacity is exhausted. |
| canonical result | Normalized logical output whose digest is independent of worker count, attempt IDs, timestamps, and paths. |
| checkpoint | Durable manifest describing a recoverable frontier or merge state; not automatically a full backup. |
| commit | Conditional durable selection of one attempt artifact as the visible task result. |
| control plane | Small messages and durable decisions for registration, scheduling, leases, status, and commits. |
| data plane | Movement or reading of dataset and result bytes, normally through immutable files in Forge. |
| dataset | Immutable, versioned collection of event files and a manifest with content identity. |
| determinism | Equal frozen inputs and supported software semantics produce equal canonical output. |
| diagnostic bundle | Bounded, redacted collection of state, logs, manifests, versions, and artifacts for investigation. |
| exactly-once visible commit | At most one result becomes authoritative per task even though physical attempts may duplicate. |
| fencing epoch | Monotonic authorization value used to reject operations from stale lease holders. |
| fault point | Named deterministic location where a test may delay, fail, corrupt, or terminate a component. |
| kernel | Registered trusted computation that consumes event batches and produces a versioned partial result. |
| lease | Time-bounded authorization for a worker attempt to execute and seek commit. |
| manifest | Canonical versioned metadata document describing data, experiment, run, artifact, benchmark, or evidence. |
| partition | Deterministic immutable range of dataset records assigned to one logical task. |
| publication | Making a validated artifact visible through the final path or authoritative result association. |
| reconciliation | Startup or maintenance process that compares durable metadata and files and classifies discrepancies. |
| reference engine | Deliberately simple sequential implementation used as a correctness oracle. |
| run | Durable execution of one validated experiment manifest over one immutable dataset identity. |
| session | Ephemeral network connection identity distinct from a durable worker identity. |
| staging | Attempt-specific creation of output before task-level commit and visibility. |
| task | Logical deterministic computation for one partition and kernel configuration. |
| worker | Service that polls for leases and supervises isolated attempt processes. |
| workload manifest | Frozen description of benchmark input, parameters, environment controls, and trial policy. |

## Spec lookup

Read [docs/spec/INDEX.md](docs/spec/INDEX.md) — a table mapping section-number ranges
(§1–§434) to files in `docs/spec/` — before implementing any component. Read the
relevant Part file in full before writing code against it; do not implement from
memory or from the index's one-line descriptions alone.

## Working agreement

- Tests before implementation.
- ADRs are written by me, not by you.
- No feature may be added ahead of its position in the critical path (§269,
  `docs/spec/part-17-roadmap.md`).
