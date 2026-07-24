# Appendix K - Configuration, CLI, and Operations Runbook

## 415. Configuration Example

    [paths]
    state_root = ".forge/state"
    dataset_root = ".forge/datasets"
    artifact_root = ".forge/artifacts"
    cache_root = ".forge/cache"
    diagnostics_root = ".forge/diagnostics"

    [coordinator]
    database = ".forge/state/forge.sqlite3"
    listen = "unix:.forge/state/coordinator.sock"
    lease_seconds = 30
    heartbeat_seconds = 5
    lease_sweep_seconds = 1
    lease_sweep_batch = 100
    max_runs_active = 8
    max_tasks_leased_global = 64
    shutdown_grace_seconds = 30

    [worker]
    worker_id_file = ".forge/state/worker-id"
    slots = 2
    attempt_timeout_seconds = 300
    cancel_grace_seconds = 5
    terminate_grace_seconds = 3
    max_pending_assignments = 2
    max_log_bytes_per_stream = 1048576
    cache_max_bytes = 10737418240

    [protocol]
    major = 1
    minor = 0
    max_payload_bytes = 1048576
    max_output_frames = 1024
    max_output_bytes = 4194304
    handshake_timeout_seconds = 5
    idle_timeout_seconds = 60

    [storage]
    validation = "full"
    sqlite_synchronous = "full"
    wal_checkpoint_policy = "observed"
    staged_retention_hours = 24
    quarantine_retention_hours = 168

    [native]
    enabled = true
    fallback_to_python = true
    min_batch_records = 4096

    [logging]
    level = "INFO"
    format = "jsonl"
    max_field_bytes = 4096
    include_source = false

## 416. Configuration Precedence

1.  Built-in safe defaults establish local paths, local binding, and conservative bounds.
2.  A named configuration file overrides defaults and is hashed into the run or service manifest.
3.  Environment variables may override secrets and deployment-specific values only; document exact names.
4.  CLI flags override file values for one invocation and are included in diagnostic output.
5.  Experiment manifests control per-run semantics only within coordinator admission limits.
6.  Unknown configuration keys are errors rather than silently ignored typos.
7.  Resolved configuration can be printed with secret values redacted and source of each value identified.

## 417. CLI Command Surface

**Table 144 --- Recommended CLI surface.**

  --------------------------------------------------------------------------------------------------------------------------------
  Command                        Responsibility
  ------------------------------ -------------------------------------------------------------------------------------------------
  forge init                     Create local directory layout and safe starter config.

  forge doctor                   Validate platform, compiler/extension, paths, permissions, SQLite, limits, and stale processes.

  forge dataset generate         Create deterministic synthetic dataset from manifest.

  forge dataset validate         Validate schema, size, digest, and partition compatibility.

  forge experiment validate      Resolve dataset/kernel and validate all parameters.

  forge coordinator start        Start durable coordinator in foreground with owned socket.

  forge worker start             Start one worker with explicit slots and capabilities.

  forge run submit               Submit experiment idempotently and print run ID.

  forge run follow               Stream bounded status changes until terminal.

  forge run status               Show run/task/attempt/result summary with JSON option.

  forge run cancel               Request idempotent cancellation and optionally follow.

  forge worker list              Show sessions, heartbeat age, slots, and active attempts.

  forge system drain             Stop admission and allow or cancel active work by policy.

  forge diagnose bundle          Create bounded redacted evidence for one run/system.

  forge diagnose verify          Run metadata/artifact/invariant checks.

  forge storage gc               Plan or execute safe cleanup with dry-run default.

  forge scenario list            List deterministic fault scenarios and requirements.

  forge scenario run             Execute one failure scenario and preserve evidence.

  forge benchmark run            Execute frozen benchmark manifest and append raw trials.

  forge evidence build           Hash, validate, and assemble release evidence bundle.
  --------------------------------------------------------------------------------------------------------------------------------

## 418. Fresh Local Deployment Runbook

    # 1. Clone and verify source.
    git clone <repository-url> forge
    cd forge
    git checkout <release-tag>
    git status --short

    # 2. Create environment and install from the release artifact or source.
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e '.[dev]'

    # 3. Verify host and initialize safe local state.
    forge doctor --strict
    forge init --root .forge-demo

    # 4. Generate and validate immutable fixture.
    forge dataset generate --manifest examples/tiny/dataset.json
    forge dataset validate --manifest examples/tiny/dataset.json --full

    # 5. Start services in separate terminals or managed demo process group.
    forge coordinator start --config examples/tiny/forge.toml
    forge worker start --config examples/tiny/forge.toml --worker-name worker-a
    forge worker start --config examples/tiny/forge.toml --worker-name worker-b

    # 6. Submit and verify.
    RUN_ID=$(forge run submit examples/tiny/experiment.json --format id)
    forge run follow "$RUN_ID"
    forge diagnose verify --run "$RUN_ID" --full

    # 7. Shut down cleanly.
    forge system drain --mode finish-active --timeout 30

## 419. Incident Triage Runbook

1.  Do not mutate the database or artifact tree immediately. Capture source/config/environment identity and current time.
2.  Run read-only status and invariant checks. Record run, task, attempt, worker, lease, and artifact identities.
3.  Create a diagnostic bundle with bounded logs, metadata snapshot, artifact descriptors, process list, versions, and disk/memory state.
4.  Determine whether the issue is no progress, correctness mismatch, missing artifact, resource exhaustion, protocol failure, or process leak.
5.  Stop admission if additional work could amplify damage. Prefer drain over abrupt kill when integrity permits.
6.  If a worker is isolated as unhealthy, drain or disable it; do not manually reassign its task outside coordinator semantics.
7.  Restart the coordinator only after preserving evidence and confirming startup reconciliation behavior for the observed state.
8.  Use documented repair commands only. Manual SQL or file moves require a copied state root and written procedure.
9.  After recovery, verify canonical result and all invariants, then convert the incident into a deterministic regression scenario.

## 420. Garbage-Collection Safety Checklist

- Default to dry run and show artifact ID, attempt ID, state, age, size, path, and reason.
- Never delete a file referenced by `task_results` or a final run manifest.
- Take the metadata decision and file action through a recoverable state such as `deleting` if necessary.
- Resolve paths beneath the artifact root without following untrusted symlinks.
- Use retention windows for staged, quarantined, diagnostic, cache, and benchmark data separately.
- Treat missing files idempotently but record the discrepancy.
- Bound each sweep by entries and bytes, and expose reclaimed totals and errors.
- Do not run an aggressive sweep concurrently with startup reconciliation or release evidence capture without coordination.
- Test process death during cleanup and ensure committed content remains protected.

## 421. Backup and Recovery Boundary

Forge is an educational local system, so its durability statement should remain narrower than a production backup promise. A coherent backup includes the SQLite database and WAL state according to SQLite backup rules, immutable dataset manifests or source references, committed artifact files, configuration, and release/source identity. Copying only the main database file while it is active in WAL mode can be inconsistent. The preferred backup implementation should use SQLite's online backup API or a clean drain/checkpoint procedure and should verify artifact digests after restore.

## 422. Operational Health Conditions

**Table 145 --- Operational health states.**

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Condition            Meaning                                                                                                                    Operator action
  -------------------- -------------------------------------------------------------------------------------------------------------------------- -----------------------------------------------------------------
  healthy              Coordinator responsive, sweeper current, no invariant failures, storage available, workers progressing.                    None.

  degraded             Reduced worker capacity, retry spike, queue pressure, long database waits, or diagnostic failure without integrity loss.   Inspect metrics and drain affected workers or reduce admission.

  blocked              No progress due to full disk, all workers unavailable, or scheduler/resource mismatch.                                     Stop admission and resolve resource/capability issue.

  integrity_failed     Missing committed artifact, database constraint failure, digest mismatch, or impossible state.                             Stop admission, preserve evidence, do not auto-repair silently.

  draining             No new work; active attempts completing or being cancelled.                                                                Wait or escalate according to shutdown policy.

  stopped              Listeners closed and background tasks stopped with restartable durable state.                                              Restart or perform maintenance.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
