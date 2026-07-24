# Part XII - Observability, Diagnostics, and Operational Understanding

## 179. Observability Principles

- Correctness comes from metadata transactions and artifacts; observability explains them but is not authoritative.
- Every log or metric has an intended question. Avoid collecting high-cardinality data without a use.
- State transitions are structured events with identities and reasons, not prose scattered across components.
- Timing is decomposed by phase so a slow run can be localized.
- Diagnostic export is bounded, redacted, versioned, and reproducible.
- Logs and metrics should remain usable during failure storms through bounds, sampling, and severity policy.

## 180. Structured Log Schema

    {
      "schema": "forge.log.v1",
      "timestamp_utc": "2026-07-22T20:15:04.123456Z",
      "severity": "INFO",
      "component": "coordinator.commits",
      "event": "task_committed",
      "run_id": "...",
      "task_id": "...",
      "attempt_id": "...",
      "worker_id": "worker-03",
      "correlation_id": 90123,
      "fencing_generation": 2,
      "duration_ns": 482109,
      "artifact_sha256": "...",
      "message": "task result committed"
    }

- Use UTC with high-resolution timestamp for chronology and monotonic durations for elapsed time.
- Event names are stable snake_case identifiers.
- Context is attached automatically through scoped logging context, not repeated manually in every call.
- Bound message and error fields. Put full safe traces into diagnostic artifacts when needed.
- Do not log full manifest parameters blindly; use allow-listed summaries and digests.
- Test that every critical transition emits the required fields.

## 181. Metric Taxonomy

**Table 63 --- Metric types and cardinality policy.**

  ---------------------------------------------------------------------------------------------------------------------------------------------------------
  Type                       Examples                                                      Label policy
  -------------------------- ------------------------------------------------------------- ----------------------------------------------------------------
  Counter                    tasks_committed_total, retries_total, protocol_errors_total   component, reason class, kernel class; no task ID

  Gauge                      active_leases, ready_window_depth, worker_slots_available     small bounded labels

  Histogram                  task_duration_seconds, commit_latency_seconds, frame_bytes    kernel implementation and phase only if bounded

  Summary in raw benchmark   p50/p95/p99 computed after run                                full manifest fields live in rows, not live metric labels

  Event-derived report       run timeline, attempt history                                 IDs allowed in logs/database rather than global metric backend
  ---------------------------------------------------------------------------------------------------------------------------------------------------------

## 182. Coordinator Metrics

- run_submissions_total by accepted/rejected reason.
- runs_current by state.
- ready_tasks_window, active_leases, lease_renewals_total, lease_expiries_total.
- scheduler_decision_seconds and no_compatible_task_total.
- metadata_transaction_seconds by semantic operation and metadata_busy_seconds.
- artifact_verification_seconds and verification_queue_depth.
- task_commit_total by committed/duplicate/stale/cancelled/error.
- event_loop_lag_seconds and expiry_processing_lag_seconds.
- recovery_seconds and recovery_actions_total by action.

## 183. Worker Metrics

- worker_state, available_slots, reconnects_total, session_duration_seconds.
- task_phase_seconds for launch, open, validate, read, parse, compute, write, digest, report.
- records_read_total, bytes_read_total, records_selected_total, bytes_written_total.
- task_peak_rss_bytes, task_cpu_seconds, task_wall_seconds.
- child_exits_total by code/signal/classification; forced_kills_total.
- cache_hits_total, cache_misses_total, cache_bytes, cache_evictions_total.
- heartbeat_jitter_seconds, renewal_rejections_total, progress_messages_total.
- staging_failures_total and cleanup_failures_total.

## 184. Run Timeline

A run timeline is one of the strongest demo artifacts. Generate it from durable state transitions and selected metrics, not from manually edited screenshots.

- Submission, planning start/end, first lease, task commits, retries, worker loss, cancellation, merge, and terminal outcome.
- Per-worker lanes showing attempts and idle intervals.
- Lease expiry and retry arrows.
- Commit winner and duplicate loser markers.
- Coordinator restart window and recovery actions.
- Optional throughput or queue-depth overlay.

## 185. Trace and Correlation Model

- A client request receives a correlation ID and run ID after creation.
- Task assignment creates an attempt span or trace segment linked to run and task.
- Worker phase spans use the same attempt identity.
- Artifact verification and commit link back to finish message correlation.
- Retries create sibling attempts, not a mutation of one span.
- OpenTelemetry is optional; a simple structured event trace is sufficient if it answers the questions.

## 186. Health and Readiness

**Table 64 --- Health and readiness signals.**

  ------------------------------------------------------------------------------------------------------------------------------------------------
  Signal                  Meaning                                                                Should fail when
  ----------------------- ---------------------------------------------------------------------- -------------------------------------------------
  process liveness        Event loop/process is running                                          fatal internal error or process unavailable

  coordinator readiness   Leadership held, metadata valid, recovery complete, listeners active   migration/recovery/invariant problem

  worker readiness        Registered and capable of accepting work                               incompatible, draining, staging unavailable

  storage health          Configured roots and metadata operations succeed                       read-only, disk full threshold, integrity error

  degraded status         Service can operate with reduced feature or capacity                   optional exporter/cache unavailable
  ------------------------------------------------------------------------------------------------------------------------------------------------

## 187. Diagnostic Bundle

**Table 65 --- Diagnostic bundle contents.**

  -------------------------------------------------------------------------------------------------
  Artifact                       Included content
  ------------------------------ ------------------------------------------------------------------
  bundle-manifest.json           schema, creation time, Forge version, included files and digests

  run-manifest.json              accepted canonical run definition

  status.json                    run/task/attempt/worker snapshots at export

  events.jsonl                   bounded relevant state transitions in order

  logs.jsonl                     redacted relevant component logs

  metrics.json                   selected counters, gauges, phase summaries

  config.redacted.toml           normalized operational configuration without secrets

  environment.json               software/hardware fingerprint and dirty-tree flag

  consistency.json               invariant scan and artifact verification report

  reproduce.sh                   safe commands or references to reproduce with known inputs
  -------------------------------------------------------------------------------------------------

The export command should state omissions and truncation. It must not silently include environment secrets, personal paths, credentials, or proprietary datasets.

## 188. Operational Thresholds

- Warning when event-loop lag approaches a meaningful fraction of heartbeat or lease interval.
- Warning when artifact verification queue remains above a threshold for a sustained interval.
- Warning or admission stop when free staging space falls below reserve.
- Warning when retry or duplicate-work ratio exceeds expected test baseline.
- Failure when an invariant scan finds committed-data inconsistency.
- Benchmark invalidation when CPU frequency, background load, dropped samples, or thermal status violates study rules.
- Thresholds are configuration and evidence, not universal production SLOs.

## 189. Observability Acceptance Criteria

- A reviewer can reconstruct one successful run and one failure/retry from logs and metadata.
- Critical state-transition events include all required IDs and before/after states.
- Metrics have bounded label cardinality and documented units.
- Run timeline and diagnostic bundle regenerate from scripts.
- Backpressure, queue saturation, event-loop lag, and recovery duration are visible.
- Redaction tests prevent secrets and unsafe paths from entering public bundles.
- Observability overload cannot cause unbounded memory growth.
