# Part XI - Python SDK, CLI, Configuration, and User Experience

## 167. Public Python Package Structure

    forge/
      __init__.py
      api/
        dataset.py
        experiment.py
        cluster.py
        run.py
        results.py
        errors.py
      config/
        models.py
        load.py
      cli/
        main.py
        render.py
      kernels/
      datasets/
      coordinator/
      worker/
      protocol/
      metadata/
      artifacts/
      observability/
      bench/
    tests/
    examples/
    docs/

Expose a small public surface from forge.\_\_init\_\_ and keep operational implementation modules private. Users should not import SQLite row types or protocol payload classes to submit an experiment.

## 168. Dataset API

    dataset = Dataset.open_manifest('data/telemetry/manifest.json')
    dataset.verify(mode='standard')

    generated = Dataset.generate_telemetry(
        output='data/generated',
        records=100_000_000,
        streams=4096,
        seed=42017,
        records_per_file=25_000_000,
    )

- Dataset objects are immutable views over a manifest and root.
- Opening parses and validates schema; verify performs configured file integrity checks.
- Generation returns only after files and canonical manifest are finalized.
- Dataset.summary() returns bounded metadata without scanning all records.
- No API mutates a registered dataset in place.

## 169. Experiment API

    experiment = Experiment(
        dataset=dataset,
        kernel=KernelRef('telemetry.stats_by_stream', version='1.0.0'),
        implementation='cpp',
        parameters={"event_type_mask": 0b10000110},
        partitioning=ContiguousRecords(target_records=1_000_000),
        retry=RetryPolicy(max_attempts=3),
        seed=42017,
    )

    experiment.validate()
    experiment.write_manifest('runs/example-experiment.json')

- The Experiment constructor remains declarative and performs lightweight type validation.
- validate resolves dataset and kernel contracts and returns all field errors together where practical.
- to_manifest produces canonical serializable data without live file handles or callables.
- Kernel parameters use typed kernel-specific models internally even if serialized as JSON.
- An experiment can be executed in reference mode before submission to a cluster.

## 170. Cluster API

    with Cluster.local(
        workers=4,
        transport='unix',
        metadata='runs/forge.db',
        artifacts='runs/artifacts',
    ) as cluster:
        run = cluster.submit(experiment, client_request_id='demo-2026-07-22')
        run.wait(show_progress=True)
        result = run.result()

Cluster.local may supervise coordinator and worker subprocesses for demos, but it should use the same public protocol and durable paths as standalone commands in socket mode. Avoid an in-memory shortcut that makes the demo unlike the tested architecture.

## 171. RunHandle API

    status = run.status(detail='tasks')
    print(status.state, status.progress.committed_tasks)

    run.cancel(reason='user requested stop')
    run.wait(timeout=60)
    bundle = run.export_diagnostics('diagnostics/run-123')

- RunHandle stores cluster connection and run ID, not mutable run state.
- status returns an immutable snapshot with a sequence or updated timestamp.
- wait uses polling or events with a timeout and handles connection loss by reconnecting.
- result is available only for SUCCEEDED and validates the final artifact descriptor.
- cancel is idempotent and returns the durable resulting state.
- export_diagnostics never includes secrets by default and records its own manifest.

## 172. Result API

- Expose final schema, exact-byte artifact descriptor, canonical digest, and bounded summary.
- Provide iterators or memory-mapped readers for large results rather than loading everything automatically.
- Keep attempt metrics and run execution history accessible but separate from logical result content.
- A compare(other) helper reports canonical equality and structured differences for demo kernels.
- Serialization to JSON or CSV is explicit and versioned; avoid repr as an interchange format.

## 173. CLI Command Map

**Table 62 --- CLI commands.**

  -------------------------------------------------------------------------------------------
  Command                        Purpose
  ------------------------------ ------------------------------------------------------------
  forge dataset generate         Create deterministic synthetic dataset and manifest.

  forge dataset verify           Validate headers, counts, ranges, and selected checksums.

  forge experiment validate      Resolve kernel and dataset and print canonical manifest.

  forge reference run            Execute one-process oracle and write result.

  forge coordinator start        Start durable coordinator and listeners.

  forge worker start             Start standalone worker and register capabilities.

  forge cluster local            Supervise local coordinator plus N workers for demo.

  forge run submit               Submit manifest with optional idempotency key.

  forge run status               Print human or JSON status, tasks, attempts, and progress.

  forge run cancel               Request idempotent cancellation.

  forge run wait                 Wait for terminal state with progress.

  forge run result               Inspect or export final result.

  forge diagnose                 Run invariant checks and export diagnostic bundle.

  forge gc                       Dry-run or perform conservative artifact cleanup.

  forge bench run                Execute frozen benchmark matrix and raw output.

  forge bench report             Generate plots and report from raw records.
  -------------------------------------------------------------------------------------------

## 174. CLI Output Rules

- Human output is concise and stable enough for demos but is not parsed by automation.
- --json emits versioned machine-readable records to stdout; logs go to stderr or configured sink.
- Exit codes distinguish success, user validation, terminal run failure, cancellation, timeout, connection, and internal errors.
- Secrets, full environment variables, arbitrary payloads, and unbounded tracebacks are not printed by default.
- Commands print or persist the exact configuration and manifest digest used.
- Destructive operations default to dry-run and require explicit confirmation or --yes in noninteractive use.

## 175. Configuration Loading

    [coordinator]
    unix_socket = "run/forge.sock"
    max_sessions = 64
    shutdown_grace_seconds = 20

    [metadata]
    url = "sqlite:///run/forge.db"
    durability = "standard"

    [artifacts]
    root = "run/artifacts"
    integrity = "standard"
    max_staged_bytes_per_attempt = 1073741824

    [leases]
    duration_seconds = 30
    heartbeat_seconds = 5
    max_attempts = 3

    [worker]
    capacity = 1
    task_timeout_seconds = 600

- Parse into frozen typed models and reject unknown keys in strict mode.
- Normalize relative paths against an explicit configuration base directory, not current working directory accidentally.
- Environment variables are reserved for deployment overrides and secrets; print redacted normalized configuration.
- Run-semantic settings are copied into the accepted manifest so later process configuration changes do not alter an existing run.
- Benchmark commands reject a configuration that uses debug builds or missing environment capture unless explicitly overridden and labeled invalid for publication.

## 176. Local Debug Mode

Provide a deterministic debug mode that runs coordinator and worker logic through in-memory adapters while preserving state machines. It is for breakpoints and unit tests, not the primary performance path.

- Use a fake clock, deterministic ID generator, in-memory metadata repository, and temporary artifact store.
- Allow stepping one scheduler event at a time.
- Expose state snapshots and invariant checks after each event.
- Replay a recorded message/event trace into the model.
- Keep debug mode clearly labeled so results are not confused with socket/multiprocess execution.

## 177. Notebook Policy

- Notebooks are for analysis and explanation, not the only copy of core logic.
- All benchmark data loading, validation, and plotting lives in importable modules with tests.
- A notebook begins by printing dataset, release, benchmark schema, and environment fingerprints.
- Outputs are cleared or intentionally frozen before commit according to repository policy.
- Plots can be regenerated by a noninteractive command for CI and evidence bundles.
- Do not hide failed or excluded samples; annotate exclusion reasons in raw data.

## 178. Python Quality Criteria

- Public functions and models are fully typed; mypy or pyright strictness is configured deliberately.
- Ruff or equivalent enforces formatting, imports, common bugs, and complexity rules without creating a giant ignore list.
- pytest fixtures isolate temporary directories, ports, clocks, and subprocesses.
- Async tests have timeouts and leave no background tasks.
- Package installation works from a clean virtual environment in reference mode and C++ mode.
- Exceptions form a documented hierarchy with stable user-facing codes.
- Examples run in CI against small fixtures.
