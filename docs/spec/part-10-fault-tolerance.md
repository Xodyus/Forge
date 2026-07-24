# Part X - Fault Tolerance, Recovery, and Chaos Engineering

## 151. Failure Philosophy

Forge assumes crash-stop process failures, temporary communication loss, storage errors, and malformed or contradictory messages. It does not assume malicious Byzantine components. The design aims to preserve unambiguous durable state and exactly one visible task result, not uninterrupted availability.

Failure handling should be tested at boundaries where state might have changed: before and after a transaction commit, before and after artifact finalize, before and after a worker report, and before and after the coordinator response. The most educational failures are uncertain outcomes, not exceptions that occur before any work begins.

## 152. Failure Taxonomy

**Table 57 --- Failure taxonomy and primary defenses.**

  ------------------------------------------------------------------------------------------------------------------------------------------------------------
  Domain                   Failure examples                                                    Primary defense
  ------------------------ ------------------------------------------------------------------- ---------------------------------------------------------------
  Client                   timeout, duplicate submit, disconnect during cancel                 idempotency keys and durable outcomes

  Coordinator process      crash, event-loop stall, forced kill                                transactional metadata and restart reconciliation

  Worker control process   crash, disconnect, restart                                          leases, fencing, retry, query-on-reconnect

  Task child               exception, signal, hang, OOM                                        supervision, timeout, typed failure, bounded retry

  Transport                fragmentation, reset, half-open, delayed messages                   framing, sequence, heartbeat, semantic IDs

  Metadata                 busy, disk full, corruption, migration error                        short transactions, constraints, integrity check, fail closed

  Artifact store           partial write, missing file, digest mismatch, cross-device rename   staging, checksums, atomic publication contract

  Environment              clock adjustment, CPU throttling, disk pressure                     monotonic deadlines, metrics, benchmark invalidation

  Code defect              illegal transition, overflow, use-after-free                        invariants, sanitizers, differential tests, diagnostic bundle
  ------------------------------------------------------------------------------------------------------------------------------------------------------------

## 153. Worker Failure Scenarios

- Crash before start: lease expires or launch failure is reported; no staged output exists.
- Crash during compute: lease expires; retry creates a new attempt and generation.
- Crash during staging: incomplete artifact lacks a finalized manifest and is never eligible for commit.
- Crash after staging before report: orphan staged output is detected by cleanup or recovery; conservative baseline retries.
- Crash after report before commit response: reconnect queries durable attempt state; worker does not assume loser or winner.
- Hang while heartbeats continue from control process: task timeout or progress watchdog handles child; session liveness alone is insufficient.
- Worker sends conflicting results for one attempt: invariant failure and quarantine.
- Worker returns success with wrong record count or digest: validation rejects commit and records integrity failure.

## 154. Coordinator Failure Scenarios

- Crash before run-creation commit: client retry creates or finds no run according to transaction outcome.
- Crash after run commit before response: client idempotency key returns the existing run.
- Crash after lease commit before assignment send: lease expires or is explicitly revoked on recovery.
- Crash after artifact verification before commit: no task state changed; worker retry/query is safe.
- Crash after commit transaction before response: reconnect or duplicate finish receives existing committed outcome.
- Crash during cancellation: recovery continues CANCELLING state and prevents new commits.
- Crash during merge: merge task follows ordinary attempt recovery.
- Crash during graceful shutdown: restart reconciliation is authoritative, not the shutdown log.

## 155. Network Failure Scenarios

**Table 58 --- Network failure behavior.**

  ----------------------------------------------------------------------------------------------------------------------------------------------
  Scenario                               Expected behavior
  -------------------------------------- -------------------------------------------------------------------------------------------------------
  Packet fragmentation/coalescing        Decoder emits the same messages independent of read boundaries.

  Worker-to-coordinator path lost        Renewals stop; coordinator eventually expires lease.

  Coordinator-to-worker path lost        Worker does not receive renewal/cancel; it stops or becomes stale according to local deadline policy.

  Half-open TCP connection               Application heartbeat/idle timeout closes session; lease policy remains separate.

  Delayed stale finish                   Fencing and task state reject commit.

  Duplicate finish after response loss   Idempotent committed or loser outcome.

  Reconnect to restarted coordinator     New session negotiates and queries durable active attempt state.

  Multi-host partition isolates worker   Worker may compute but cannot retain authority indefinitely; later result is stale.
  ----------------------------------------------------------------------------------------------------------------------------------------------

## 156. Fencing Token Correctness

Fencing is the defense against a slow or partitioned worker acting after a newer attempt has authority. A token is useful only if every authority-sensitive operation checks it.

- Lease renewal checks generation.
- Start acknowledgment checks generation.
- Progress may be recorded as stale diagnostics but cannot extend authority without generation check.
- Stage/finish checks generation and task state according to commit policy.
- Artifact naming includes attempt identity so a stale writer cannot overwrite a newer attempt.
- Any external side-effect adapter would also need to enforce a fencing or idempotency key; the core cannot protect an unaware external system.
- Generation increment and lease creation occur in one transaction.

## 157. Exactly-Once Visible Commit, Precisely Stated

> For each logical task in a run, Forge records at most one committed attempt and exposes at most one committed artifact reference. Task code may execute more than once. Attempt-scoped output may be written more than once. A conditional metadata transaction selects one valid staged attempt; all later or racing attempts are non-visible losers. This guarantee applies inside Forge's metadata and artifact publication boundary and does not make arbitrary external kernel side effects exactly once.

Use this wording, or a shorter equivalent, in the README. Avoid the unqualified phrase exactly once because reviewers will ask whether it refers to execution, delivery, effects, or visibility.

## 158. Commit Race Cases

**Table 59 --- Commit race resolution.**

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Race                                                        Winner rule                                                Loser handling
  ----------------------------------------------------------- ---------------------------------------------------------- -------------------------------------------------------
  Two valid attempts finish concurrently                      First successful conditional commit transaction            Return duplicate loser; retain/clean staged artifact.

  Finish races with cancellation                              Transaction order and state predicate                      If cancellation wins, reject commit.

  Finish races with lease expiry/retry                        Current-generation policy or explicit speculation policy   Stale attempt rejected.

  Duplicate same finish message                               Existing matching committed/staged outcome                 Idempotent response.

  Same attempt reports different digest                       No winner until investigation                              Invariant failure; quarantine.

  Artifact disappears after verification before transaction   Transaction or final publication rechecks existence        Reject and record storage failure.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 159. Checkpoint and Restart Strategy

The SQLite database and immutable artifacts are sufficient for local recovery. Checkpoint manifests are useful for evidence, export, and faster inspection, but they must be derived from a consistent durable point.

1.  Begin a read transaction or obtain a metadata snapshot identity.
2.  Read run manifest digest, run state, committed tasks, terminal failures, current merge state, and artifact descriptors.
3.  Write checkpoint JSON to a temporary artifact and calculate digest.
4.  Finalize and publish the checkpoint artifact.
5.  Record the checkpoint reference and metadata sequence in the database.
6.  On import or inspection, verify run manifest, checkpoint digest, schemas, and every referenced committed artifact.

## 160. Clock and Deadline Failures

- Use time.monotonic_ns for in-process lease timers, timeout durations, and benchmark intervals.
- Use UTC wall-clock timestamps for durable human chronology and cross-process records.
- After restart, reconstruct lease policy conservatively from persisted expiry and restart time; monotonic values from the old process are meaningless.
- A backward or forward wall-clock jump must not create an older fencing generation or allow a committed task to reopen.
- Inject clock jumps into tests through a fake clock abstraction.
- Record scheduler lag separately from lease duration so an overloaded coordinator can be diagnosed.

## 161. Single-Leader and Split-Brain Boundary

Gate A and B support one coordinator. Use a lock that is valid for the deployment: an exclusive file lock may be sufficient on one host; a database row or external lease may be needed for a trusted multi-host experiment. Do not claim automatic high availability.

- A second coordinator must fail startup or remain read-only.
- Leadership acquisition precedes recovery and listener readiness.
- Leadership loss during operation triggers fail-closed shutdown.
- Workers include coordinator/session generation in handshake if needed to reject messages from a prior leader process.
- A multi-host shared filesystem lock may have subtle semantics; test the actual environment or restrict scope.

## 162. Fault Injection Framework

Faults should be named, scoped, deterministic, and observable. Avoid scattered random sleep calls that create irreproducible flakes.

    class FaultInjector(Protocol):
        async def hit(self, point: str, context: Mapping[str, object]) -> None: ...

    # Example points
    # coordinator.after_lease_commit
    # coordinator.before_commit_transaction
    # artifact.after_data_fsync
    # worker.after_stage_finalize
    # worker.before_finish_send
    # metadata.before_transaction_commit

- A no-op injector is used in normal runs.
- Test injectors trigger on exact occurrence count, entity ID, seed, or predicate.
- Actions include raise typed error, delay until released, terminate process, truncate file, drop message, duplicate message, or return disk-full error.
- Each triggered fault emits an evidence record outside the component being killed when possible.
- Fault points are stable test interfaces and should not reveal secrets or change hot paths materially in release builds.

## 163. Crash-Point Testing

For critical sequences, enumerate crash points and restart after each one. The objective is not only that the program starts; the recovered state must satisfy invariants and the run must have a documented outcome.

**Table 60 --- Critical crash-point sequences.**

  ---------------------------------------------------------------------------------------------------------------------------------------------
  Sequence                       Crash points
  ------------------------------ --------------------------------------------------------------------------------------------------------------
  Run creation                   before transaction, during inserts, after commit, before response

  Lease assignment               before transaction, after attempt insert, after commit, before send, after send

  Artifact staging               after create, mid-write, after flush, after rename, after manifest

  Task commit                    after verification, before transaction, after artifact row, after task update, after commit, before response

  Cancellation                   before state change, after CANCELLING commit, during worker notifications, before final CANCELLED

  Merge completion               after map frontier, during merge staging, after final commit, before run SUCCEEDED

  Checkpoint                     during snapshot read, mid-write, after finalize, before DB reference
  ---------------------------------------------------------------------------------------------------------------------------------------------

## 164. Chaos Scenario Catalog

**Table 61 --- Chaos and recovery scenarios.**

  ------------------------------------------------------------------------------------------------------------------------------------------
  Scenario                       Expected evidence
  ------------------------------ -----------------------------------------------------------------------------------------------------------
  CHAOS-001                      Kill one worker at 50% progress; verify one retry and one committed result.

  CHAOS-002                      Kill every worker sequentially; run remains RUNNING until retry budget or replacement workers.

  CHAOS-003                      Pause coordinator event loop beyond lease duration in a controlled test; document mass-expiry policy.

  CHAOS-004                      Terminate coordinator after a commit transaction but before response; duplicate finish returns committed.

  CHAOS-005                      Drop every third heartbeat while data messages continue; lease behavior remains defined.

  CHAOS-006                      Duplicate and reorder allowable messages within protocol constraints; idempotency holds.

  CHAOS-007                      Fill staging disk during output; attempt fails without publishing partial data.

  CHAOS-008                      Corrupt one staged result byte before verification; commit is rejected.

  CHAOS-009                      Remove committed artifact before restart; recovery fails closed.

  CHAOS-010                      Cancel while two attempts race; no post-cancel commit occurs.

  CHAOS-011                      Restart worker after unknown commit outcome; query resolves cleanup decision.

  CHAOS-012                      Start second coordinator; leadership protection prevents scheduling.

  CHAOS-013                      Slow artifact verifier saturates queue; control-plane backpressure remains bounded.

  CHAOS-014                      Introduce a deterministic long-tail partition; straggler metrics identify it.

  CHAOS-015                      Truncate metadata copy or fail migration fixture; readiness stays false.
  ------------------------------------------------------------------------------------------------------------------------------------------

## 165. Recovery Metrics

- Failure detection latency: event to coordinator classification.
- Lease expiry latency: scheduled expiry to processed expiry.
- Retry scheduling latency: expiry/failure to new lease.
- Lost work: records, bytes, and CPU time executed by noncommitted attempts.
- Coordinator restart time: process start to readiness, broken into open, migrate, scan, verify, rebuild.
- Run recovery delay: failure to resumed useful progress.
- Duplicate work ratio: noncommitted attempt CPU / total attempt CPU.
- Cleanup lag and orphan bytes after fault scenarios.

## 166. Fault-Tolerance Acceptance Criteria

- Every failure in the published chaos catalog has a deterministic test or scripted demonstration.
- The task and run invariants hold after every crash-point restart.
- No partial or stale result becomes committed.
- Client, worker, and coordinator retries are idempotent at defined boundaries.
- Missing committed data fails visibly rather than being silently recomputed.
- Recovery and failure-detection timings are measured and labeled by policy settings.
- The README states the single-leader, trusted-kernel, local-first, and exactly-once-visible boundaries precisely.
