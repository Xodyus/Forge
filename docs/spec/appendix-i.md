# Appendix I - Verification Harness and Failure-Scenario Schemas

## 401. Suggested Test Directory

    tests/
    ├── unit/
    │   ├── domain/
    │   ├── manifests/
    │   ├── dataset/
    │   ├── coordinator/
    │   ├── worker/
    │   └── protocol/
    ├── property/
    │   ├── state_machines/
    │   ├── partitioning/
    │   ├── framing/
    │   └── merge/
    ├── differential/
    │   ├── kernels/
    │   ├── python_cpp/
    │   └── distributed_reference/
    ├── integration/
    │   ├── embedded/
    │   ├── unix_socket/
    │   ├── tcp/
    │   └── package_install/
    ├── recovery/
    │   ├── worker_crashes/
    │   ├── coordinator_crashes/
    │   ├── commit_races/
    │   ├── cancellation/
    │   ├── storage_faults/
    │   └── scenarios/
    ├── fuzz/
    │   ├── protocol/
    │   ├── dataset/
    │   └── native/
    ├── soak/
    └── fixtures/

## 402. Failure Scenario Manifest

    schema: forge.failure-scenario
    schema_version: 1
    scenario_id: worker-killed-after-descriptor-fsync
    seed: 17

    fixture:
      dataset_manifest: tests/fixtures/tiny/dataset.json
      experiment_manifest: tests/fixtures/tiny/experiment.json
      workers: 2
      worker_slots: 1

    faults:
      - target: worker
        selector:
          attempt_ordinal: 0
        point: after_artifact_descriptor_fsync
        action: kill_process_group
        occurrence: 1

    expect:
      run_state: succeeded
      task_states:
        committed: all
      retries:
        minimum: 1
        maximum: 1
      invariant_failures: 0
      canonical_result_matches_reference: true
      stale_commit_rejections:
        minimum: 0
      orphaned_committed_artifacts: 0

    timeouts:
      scenario_seconds: 60
      no_progress_seconds: 10

    preserve:
      metadata_snapshot: true
      structured_events: true
      process_logs: true
      artifact_tree: true
      diagnostic_bundle: true

## 403. Fault-Point Catalog

**Table 141 --- Deterministic fault-point catalog.**

  ------------------------------------------------------------------------------------------------------------------------------------------------------
  ID              Component       Injection point                                Required semantic outcome
  --------------- --------------- ---------------------------------------------- -----------------------------------------------------------------------
  FP-001          coordinator     before assignment transaction                  No attempt or lease exists.

  FP-002          coordinator     after assignment commit before response        Worker may retry poll; assignment is discoverable/idempotent.

  FP-003          worker          after child start before started message       Lease expires or worker reconnect reports owned attempt.

  FP-004          child           during dataset read                            Attempt fails or disappears; no valid descriptor.

  FP-005          child           after result temp write before file fsync      Partial temp never treated as staged.

  FP-006          child           after result fsync before descriptor write     Complete unreferenced output reconciled or cleaned.

  FP-007          child           after descriptor fsync before parent outcome   Valid attempt artifact may exist without completion.

  FP-008          worker          after staged message before commit reply       Duplicate completion is idempotent or returns existing decision.

  FP-009          coordinator     before commit transaction                      No visible result; retry may win.

  FP-010          coordinator     after commit transaction before response       Retry of completion discovers committed result.

  FP-011          coordinator     between metadata and file publication step     Startup reconciliation follows selected publication protocol.

  FP-012          coordinator     after file publication before terminal event   Durable state/result remains authoritative; event may be regenerated.

  FP-013          worker          during cancellation grace period               Supervisor escalates and reaps process.

  FP-014          transport       partial header then disconnect                 Decoder releases bounded state and no semantic action occurs.

  FP-015          transport       partial payload then reconnect                 Old connection state discarded; message retried with idempotency.

  FP-016          storage         fsync failure                                  No false staged/committed state; typed storage error.

  FP-017          storage         checksum mismatch during verification          Artifact rejected and attempt classified.

  FP-018          coordinator     during run cancellation transaction            Repeat cancellation converges idempotently.

  FP-019          merge           after partial final output write               Temporary merge artifact removed/recovered; run not successful.

  FP-020          diagnostics     bundle file unavailable                        Core run unaffected; diagnostic failure is explicit and bounded.
  ------------------------------------------------------------------------------------------------------------------------------------------------------

## 404. Property Inventory

**Table 142 --- Core property inventory.**

  ------------------------------------------------------------------------------------------------------------------------------
  Property                       Statement
  ------------------------------ -----------------------------------------------------------------------------------------------
  P-001                          Partition ranges are ordered, nonoverlapping, aligned, and exactly cover the dataset.

  P-002                          Canonical partition IDs are stable for equal inputs and policy version.

  P-003                          No task has more than one visible result.

  P-004                          A committed result comes from the task current fencing epoch.

  P-005                          A terminal task has no active attempt.

  P-006                          A successful run has all required tasks committed and a verified final digest.

  P-007                          Repeated submission with one idempotency key creates no duplicate run.

  P-008                          Repeated completion message converges to one commit decision.

  P-009                          Expired/stale heartbeat cannot renew a newer attempt.

  P-010                          Decoder output is invariant to input chunking.

  P-011                          Encoder/decoder round trip preserves all supported fields.

  P-012                          Protocol and file lengths exceeding limits are rejected before proportional allocation.

  P-013                          Distributed canonical output equals sequential reference for generated supported experiments.

  P-014                          Python and C++ kernels agree on valid corpus and compatible errors on invalid corpus.

  P-015                          Cancellation is idempotent and no new lease is issued after the admission barrier.

  P-016                          Cleanup never deletes an artifact referenced by a committed result.

  P-017                          Restart reconciliation is idempotent.

  P-018                          All queues, logs, frames, batches, and status pages respect configured limits.

  P-019                          Same release, manifest, and supported worker count produce same canonical result digest.

  P-020                          Every public quantitative claim identifies an immutable evidence item.
  ------------------------------------------------------------------------------------------------------------------------------

## 405. Test Command Matrix

    # Fast developer checks
    python -m ruff check .
    python -m ruff format --check .
    python -m mypy src
    python -m pytest tests/unit tests/property -q

    # Native debug and sanitizer checks
    cmake --preset debug
    cmake --build --preset debug
    ctest --preset debug --output-on-failure
    cmake --preset asan-ubsan
    cmake --build --preset asan-ubsan
    ctest --preset asan-ubsan --output-on-failure

    # Integration and connected runtime
    python -m pytest tests/integration/embedded -m integration
    python -m pytest tests/integration/unix_socket -m integration

    # Selected deterministic recovery suite
    python -m pytest tests/recovery -m recovery --scenario-seed 17
    forge scenario run --catalog tests/recovery/scenarios --profile release-smoke

    # Differential and longer generated corpus
    python -m pytest tests/differential -m slow
    python -m pytest tests/property -m slow --hypothesis-profile nightly

    # Fuzz harness examples; exact command depends on chosen engine/tool.
    python -m pytest tests/fuzz/protocol --fuzz-seconds 60
    cmake --build --preset fuzz
    ./build/fuzz/forge_event_decoder -max_total_time=60 corpus/event

    # Package clean install
    python -m build
    python -m venv .tmp-release-venv
    .tmp-release-venv/bin/pip install dist/*.whl
    .tmp-release-venv/bin/forge demo verify --fixture examples/tiny

## 406. Crash Matrix Result Schema

    {
      "scenario_id": "worker-killed-after-descriptor-fsync",
      "scenario_version": 1,
      "seed": 17,
      "source_commit": "<sha>",
      "started_at_utc": "<time>",
      "duration_seconds": 3.421,
      "faults_triggered": [
        {
          "fault_point": "FP-007",
          "target_instance": "<worker/attempt>",
          "occurrence": 1
        }
      ],
      "observed": {
        "attempts": 2,
        "retries": 1,
        "commit_rejections": 0,
        "coordinator_restarts": 0,
        "worker_restarts": 0
      },
      "final": {
        "run_state": "succeeded",
        "canonical_result_sha256": "<digest>",
        "reference_result_sha256": "<same digest>",
        "invariant_failures": []
      },
      "artifacts": {
        "diagnostic_bundle": "recovery/...tar.zst",
        "timeline": "recovery/...jsonl",
        "metadata_snapshot": "recovery/...sqlite"
      }
    }

## 407. Flaky-Test Quarantine Policy

- A flaky test is treated as a correctness defect in the test system, not retried silently until green.
- Record the seed, host, timing, logs, process tree, and diagnostic bundle from the first failure.
- A temporary quarantine requires an issue, owner, reason, expiration date, and statement of which release gate it blocks.
- Do not remove the assertion merely because the race is difficult to reproduce.
- Replace sleep-based coordination with named barriers, observable state, or fake clocks where the behavior permits.
- Repeated CI retries may collect evidence but may not convert a failing required gate into success.
- Release evidence must state any quarantined scenario and cannot make the guarantee that scenario was intended to support.
