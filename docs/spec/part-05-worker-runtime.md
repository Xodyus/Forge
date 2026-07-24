# Part V - Worker Runtime, Process Supervision, and Task Execution

## 71. Worker Responsibilities and Trust Model

A worker is a replaceable executor. It may read immutable input, run a trusted registered kernel, stage output, and report telemetry. It cannot change run state, extend a lease without coordinator approval, or decide that its result is committed.

**Table 32 --- Worker responsibilities.**

  ------------------------------------------------------------------------------------------------------------------------------------------------
  Worker responsibility          Required behavior
  ------------------------------ -----------------------------------------------------------------------------------------------------------------
  Session management             Negotiate protocol, register capabilities, heartbeat, reconnect, and drain without hiding lease state.

  Task supervision               Launch or invoke one attempt under a bounded resource and cancellation policy.

  Input validation               Verify assignment, dataset schema, partition boundaries, and selected integrity checks before kernel execution.

  Kernel dispatch                Resolve an exact registered Python or C++ implementation and validate parameters.

  Output staging                 Write only to an attempt-specific path, finalize bytes, calculate digest, and report a descriptor.

  Failure reporting              Normalize exceptions and process exits into bounded typed reports.

  Telemetry                      Report progress, resource use, timing, bytes, and kernel counters without overwhelming the control plane.

  Cleanup                        Remove temporary task resources; never remove committed data based only on local belief.
  ------------------------------------------------------------------------------------------------------------------------------------------------

## 72. Recommended Worker Package Layout

    forge/worker/
      app.py              # process entry point and dependency wiring
      session.py          # coordinator connection and protocol lifecycle
      runtime.py          # assignment-to-attempt orchestration
      supervisor.py       # child process launch, cancel, timeout, reap
      child_main.py       # task-process entry point
      inputs.py           # partition validation and readers
      outputs.py          # staging writer and result descriptor
      registry.py         # Python and C++ kernel resolution
      resources.py        # limits and resource accounting
      cache.py            # bounded immutable local cache
      telemetry.py        # progress, metrics, normalized errors
      signals.py          # shutdown and cancellation handling

## 73. Worker Lifecycle

1.  Load configuration, validate local directories, and create a unique session ID.
2.  Connect to the configured coordinator with bounded exponential reconnect backoff.
3.  Negotiate protocol major/minor version and maximum frame limits.
4.  Register worker identity, software version, kernel capabilities, architecture, and capacity.
5.  Enter IDLE and heartbeat on the coordinator schedule.
6.  Request work only when a local execution slot and staging capacity are available.
7.  Validate assignment and acknowledge start after the child task process is successfully launched or the in-process task is ready.
8.  Supervise execution, renew the lease, relay bounded progress, and react to cancellation or stale-lease responses.
9.  Finalize output or normalize failure, report it idempotently, and wait for the coordinator outcome.
10. Clean attempt-local resources according to commit or loser response, return to IDLE, or enter DRAINING/QUARANTINED.
11. On shutdown, stop requesting work, cancel or drain active task according to policy, close the session, and reap all children.

## 74. Worker Startup and Capability Advertisement

Startup must prove that the worker can execute the capabilities it advertises. A capability is not a string copied from configuration; it is a checked combination of software, kernel registry, architecture, and resource availability.

### Design contract

- The worker verifies its package version and optional clean build digest.
- Every advertised kernel can be imported or loaded and reports an exact logical version.
- The worker records Python version, C++ extension build metadata, operating system, architecture, and available memory/CPU limits.
- Staging and cache directories are isolated under configured roots and pass write/read tests.
- Advertised concurrency does not exceed the configured or detected resource budget.
- A worker with a missing required extension advertises only supported Python kernels rather than failing ambiguously.

### Implementation sequence

1.  Construct WorkerCapabilities from runtime probes and registry enumeration.
2.  Create a startup self-test that runs a tiny fixture through each required kernel implementation.
3.  Resolve a stable worker ID from configuration or installation state and a fresh session ID per connection.
4.  Capture a bounded environment fingerprint for diagnostics.
5.  Register and compare coordinator-accepted capability set; refuse tasks outside the accepted set.
6.  Expose a local --self-test command used by CI and deployment scripts.

### Verification evidence

- Startup fails clearly with unwritable staging, incompatible extension, or invalid capacity.
- Advertised kernels match what dispatch can actually execute.
- Two sessions with the same worker ID follow the replacement policy.
- A worker reconnect retains identity but receives a new session generation.
- Self-test output is deterministic and contains no secrets.

### Failure modes and review questions

- The extension loads but was compiled against an incompatible Python ABI.
- The configured cache or staging root is a symlink outside the allowed root.
- Available disk space falls below a safe threshold after startup.
- Container CPU limits differ from host CPU count.
- A kernel registration import performs unexpected side effects.

## 75. Assignment Validation

- Validate message schema and protocol version before constructing paths or importing a kernel.
- Confirm worker/session identity, task ID, attempt ID, run ID, and lease generation are present and internally coherent.
- Confirm the requested kernel ID, logical version, implementation, and parameters match an accepted capability.
- Resolve dataset and output references through root-confined artifact helpers; reject absolute or escaping paths.
- Verify partition boundaries are within the manifest and aligned to the dataset format.
- Check resource profile against local limits before starting a child process.
- Reject duplicate active assignment for the same local slot. An identical retransmission may return the known state idempotently.
- Acknowledge start only after the runtime has ownership of a child process or a controlled in-process invocation.

## 76. Child Task Process Model

The strongest local design uses a small worker control process and a separate task child. The control process remains responsive to heartbeats, cancellation, and coordinator messages even when a Python kernel blocks, leaks memory, crashes the interpreter, or enters C++ code. The child receives an immutable serialized TaskLaunchSpec through a pipe or temporary manifest and returns a bounded TaskExitReport.

The baseline may execute trusted kernels in the worker process during the MVP, but the public Gate B release should supervise a child if time permits. Process supervision is a clearer systems signal than adding worker concurrency prematurely.

    @dataclass(frozen=True)
    class TaskLaunchSpec:
        run_id: str
        task_id: str
        attempt_id: str
        fencing_generation: int
        kernel: KernelRef
        partition: PartitionDescriptor
        parameters_json: bytes
        seed: int
        staging_path: str
        limits: ResourceLimits

    @dataclass(frozen=True)
    class TaskExitReport:
        outcome: Literal['staged', 'failed', 'cancelled']
        artifact: ArtifactDescriptor | None
        error: NormalizedTaskError | None
        metrics: TaskMetrics

## 77. Process Start Method and File Descriptor Hygiene

- Prefer spawn or forkserver semantics for clarity and safety when threads, event loops, and C++ libraries are present. Document Linux-specific choices.
- Pass only explicit launch data. Do not rely on inheriting coordinator or worker global objects into the child.
- Close unrelated file descriptors and mark descriptors close-on-exec where appropriate.
- Create a dedicated control pipe or socketpair for cancellation and final report; bound message size.
- Set a process group or retain a pidfd where supported so termination targets the correct child and descendants.
- Reap every child and record exit code, signal, wall time, and whether a structured report was received.
- A child process crash before report becomes a normalized transient or terminal failure according to policy; it must not hang the worker slot.

## 78. Cancellation and Timeout Escalation

**Table 33 --- Worker cancellation escalation.**

  --------------------------------------------------------------------------------------------------------------------------------------------------------------
  Phase                 Action                                                                                  Evidence
  --------------------- --------------------------------------------------------------------------------------- ------------------------------------------------
  Cooperative request   Send cancellation token or control message; kernel checks between batches.              cancel_requested timestamp and acknowledgment.

  Grace period          Continue heartbeat while waiting for child to stop and close staging safely.            grace duration and progress.

  Terminate             Send SIGTERM or platform equivalent to child/process group.                             signal and timestamp.

  Kill                  After hard deadline, send SIGKILL and reap.                                             forced_kill counter and exit status.

  Cleanup               Close partial output, mark staging incomplete, release local resources.                 cleanup result and remaining paths.

  Report                Send CANCELLED or timeout failure if lease is still current; tolerate stale response.   typed coordinator outcome.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------

Timeout is a policy attached to the attempt or kernel, not a substitute for lease expiry. A worker may terminate a child because of a local task timeout while its coordinator lease is still valid, then report a typed timeout failure. Conversely, a stale lease may require cancellation even when the kernel has not exceeded its own timeout.

## 79. Resource Limits and Accounting

**Table 34 --- Task resource controls and measurements.**

  ----------------------------------------------------------------------------------------------------------------------------------------------------
  Resource              Baseline mechanism                          Recorded metric                 Limitation
  --------------------- ------------------------------------------- ------------------------------- --------------------------------------------------
  Wall time             Monotonic timer in worker                   duration_ns                     Includes I/O and scheduling.

  CPU time              resource.getrusage or process accounting    user_ns, system_ns              Children and platform handling must be explicit.

  Memory                Peak RSS from child and optional sampling   peak_rss_bytes                  Sampling may miss short peaks.

  Open files            RLIMIT_NOFILE and startup checks            open_fd_peak if measured        Portable measurement varies.

  Address space         RLIMIT_AS where appropriate                 limit and exit classification   May interact poorly with allocators or mmap.

  Output bytes          Staging writer hard limit                   bytes_written                   Compressed and logical sizes differ.

  Input bytes/records   Reader counters                             bytes_read, records_read        Page cache affects physical I/O.

  CPU affinity          Benchmark-only sched_setaffinity            assigned CPUs                   Not a general isolation boundary.
  ----------------------------------------------------------------------------------------------------------------------------------------------------

Avoid presenting rlimits as a secure sandbox. They are operational safeguards for trusted kernels. Container or cgroup experiments may be added later, but the security boundary remains explicit.

## 80. Input Reader Design

- Open files read-only and validate the dataset header before applying partition offsets.
- Use pread, buffered reads, or mmap behind a common batch reader so the benchmark can compare them.
- Return batches aligned to whole records and cap batch bytes independently of partition size.
- Check short reads and file truncation explicitly; never treat them as an empty successful partition.
- Expose record count, bytes, parse failures, and checksum validation time.
- For mmap, handle page-aligned mapping offsets and slice to logical boundaries; do not assume a partition start is page aligned.
- The reader owns file/mapping lifetime until the C++ or Python consumer has finished with the batch.

## 81. Attempt-Scoped Output Staging

The output writer is the only supported way for a kernel to produce durable result bytes. It enforces root confinement, uniqueness, size limits, close/finalize order, and digest calculation.

1.  Create a staging directory under run/task/attempt identity with exclusive creation semantics.
2.  Write a temporary data file and a small metadata sidecar or in-memory descriptor.
3.  Reject writes after cancellation or configured output limit.
4.  Flush language buffers, close the file, and apply the configured durability operation such as fsync.
5.  Calculate digest over final bytes, preferably while streaming or in a separate bounded verification phase.
6.  Atomically rename temporary file to an attempt-finalized staging name on the same filesystem.
7.  Write a finalized attempt manifest containing schema, bytes, records, digest, and kernel metadata.
8.  Return a descriptor to the worker control process; do not rename to the committed path locally.

A partially written or unfinalized file is never reported as staged. If the process dies, recovery or garbage collection can identify incomplete attempt directories from missing finalized manifests.

## 82. Bounded Local Cache

A local cache is optional and should cache immutable verified input or compiled kernel resources, never mutable task state. It adds a data-locality signal only if measured.

- Key cache entries by immutable digest and format version, not by a path that may be reused.
- Use an explicit byte budget and eviction policy; record hits, misses, evictions, and verification time.
- Verify cached content on insert and optionally on read according to integrity mode.
- Do not cache attempt staging or committed output under ambiguous names.
- A cache miss must remain functionally correct. The cache is never required for recovery.
- Benchmark warm-cache and cold-cache cases separately and disclose page-cache effects.

## 83. Progress and Telemetry Policy

- Progress fields are monotonic counters such as records_processed, bytes_read, and batches_completed.
- Rate-limit progress messages by time and meaningful delta; a per-record message is forbidden.
- Carry task and attempt identity and fencing generation on every progress or finish message.
- Do not treat progress as a lease renewal unless the message explicitly contains a valid renewal request.
- Bound error messages and stack traces; preserve a full local traceback in the diagnostic artifact when safe.
- Record phase timings separately: open, validate, read, parse, compute, write, digest, close, report.
- Telemetry failures should not corrupt a task result, but loss of required lease renewal must still be observable.

## 84. Worker Crash and Reconnect Semantics

**Table 35 --- Worker crash points and outcomes.**

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Failure point                               Local consequence                     Coordinator consequence
  ------------------------------------------- ------------------------------------- ------------------------------------------------------------------------------------------
  Before start acknowledgment                 Child absent or launch incomplete     Lease expires or worker reports launch failure; task retries.

  During input read                           Partial local buffers discarded       Lease expires; no staged result.

  During output write                         Incomplete staging remains            Lease expires; garbage collector later removes incomplete path.

  After finalize before report                Valid staged artifact may exist       Conservative baseline retries and later cleans orphan; optional recovery may inspect it.

  After report before response                Worker does not know commit outcome   On reconnect, query attempt state idempotently before deleting artifact.

  After commit response                       Worker may crash before cleanup       Committed state remains; cleanup is idempotent.

  Control session lost, child still running   Worker may continue briefly           Lease eventually expires; stale generation prevents commit.
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 85. Worker Acceptance Test Matrix

**Table 36 --- Worker acceptance tests.**

  ---------------------------------------------------------------------------------------------------------------------
  Test ID                        Acceptance case
  ------------------------------ --------------------------------------------------------------------------------------
  WORK-001                       Worker self-test advertises only executable kernel versions.

  WORK-002                       Invalid assignment is rejected before a child process starts.

  WORK-003                       Child crash is reaped and reported without losing session responsiveness.

  WORK-004                       Cooperative cancellation closes output and returns within grace.

  WORK-005                       Unresponsive child is terminated and then killed after hard deadline.

  WORK-006                       Staging path cannot escape configured root through .. or symlink.

  WORK-007                       Output size limit stops a runaway kernel.

  WORK-008                       Partial output never produces a staged descriptor.

  WORK-009                       Duplicate coordinator response and reconnect are handled idempotently.

  WORK-010                       Memory and time metrics are recorded for success, failure, and cancellation.

  WORK-011                       Worker remains responsive to heartbeat while child executes CPU-bound Python or C++.

  WORK-012                       Cache corruption is detected and falls back or fails according to integrity policy.

  WORK-013                       Shutdown reaps children and leaves no open staging writer.

  WORK-014                       A stale lease response prevents further result reporting as current.
  ---------------------------------------------------------------------------------------------------------------------
