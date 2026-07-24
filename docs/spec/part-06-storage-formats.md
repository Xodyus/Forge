# Part VI - Dataset, Artifact, Metadata, and Checkpoint Formats

## 86. Storage Design Principles

- Inputs and published outputs are immutable; mutable coordination state lives in the metadata database.
- Every durable format begins with a version or magic value and validates lengths before allocation or interpretation.
- Paths are references, not authority. Metadata state and digest verification determine whether an artifact is committed.
- Attempt outputs are unique and staged; committed outputs are immutable and content-identified where practical.
- Atomic rename guarantees are used only within one filesystem and are documented as a deployment assumption.
- Checksums detect accidental corruption; they do not authenticate an untrusted source unless combined with trusted signatures or channels.
- Garbage collection never guesses from file age alone. It consults durable references and applies a conservative retention window.

## 87. Synthetic Event Dataset

The recommended public workload is domain-neutral synthetic telemetry. It is simple enough to validate independently but rich enough to exercise parsing, filtering, grouping, rolling state, and deterministic generation.

    struct EventRecordV1 {
        std::uint64_t sequence;      // globally increasing in generated file
        std::int64_t  timestamp_ns;  // deterministic event time
        std::uint32_t stream_id;     // grouping key
        std::uint16_t event_type;    // small registered category
        std::uint16_t flags;         // schema-defined bit field
        std::int64_t  value;         // signed measurement or delta
    };
    static_assert(sizeof(EventRecordV1) == 32);

The record uses fixed-width little-endian fields and no pointers or compiler-dependent serialization. The on-disk writer encodes each field explicitly rather than writing a native struct blindly; the static assertion is useful for in-memory layout but does not define wire endianness or packing by itself.

## 88. Dataset File Header

**Table 37 --- Dataset file header v1.**

  ----------------------------------------------------------------------------------------------------------------------------
  Offset          Bytes           Field                                 Validation
  --------------- --------------- ------------------------------------- ------------------------------------------------------
  0               8               magic = FORGEV1\\0                    Exact byte match.

  8               2               major_version                         Must equal supported major.

  10              2               minor_version                         Unsupported optional features handled by flags.

  12              2               header_bytes                          At least minimum and within file.

  14              2               record_bytes                          32 for EventRecordV1.

  16              4               flags                                 Unknown required flags reject.

  20              4               file_index                            Matches manifest position.

  24              8               record_count                          Consistent with payload length.

  32              8               first_sequence                        Used for validation and diagnostics.

  40              8               last_sequence                         Coherent with count or empty-file rule.

  48              8               generator_seed                        Informational and reproducibility evidence.

  56              8               payload_xxhash64 or reserved digest   Fast integrity check; full SHA-256 in manifest.

  64              variable        future header extension               Skipped using header_bytes after version validation.
  ----------------------------------------------------------------------------------------------------------------------------

## 89. Dataset Manifest

    {
      "schema": "forge.dataset.v1",
      "dataset_id": "telemetry-100m-seed-42017",
      "record_schema": "forge.event_record.v1",
      "endianness": "little",
      "generator": {
        "name": "forge-synth",
        "version": "1.0.0",
        "seed": 42017,
        "parameters": {
          "streams": 4096,
          "event_types": 8,
          "timestamp_step_ns": 1000
        }
      },
      "files": [
        {
          "file_id": 0,
          "path": "part-00000.fev",
          "bytes": 3200000064,
          "records": 100000000,
          "first_sequence": 0,
          "last_sequence": 99999999,
          "sha256": "..."
        }
      ],
      "total_records": 100000000,
      "manifest_sha256": "..."
    }

- Manifest paths are relative to the registered dataset root and normalized with forward slashes in canonical form.
- The manifest digest is computed without the manifest_sha256 field or with a defined placeholder to avoid recursion.
- File sizes, counts, sequence ranges, and checksums are validated at registration or according to integrity mode.
- A dataset may contain several files, but a baseline partition does not cross a file boundary.
- Generator parameters and version make public workloads reproducible without checking a huge dataset into Git.

## 90. Deterministic Dataset Generator

1.  Validate requested record count, stream count, event-type count, timestamp policy, output splitting, and seed.
2.  Use a specified pseudorandom generator with stable algorithm and explicit state, not the default generator whose algorithm may change.
3.  Generate sequence numbers and timestamps deterministically. Introduce skew, bursts, or correlations only through named parameters.
4.  Encode fields explicitly into bounded output buffers and stream to files.
5.  Calculate fast payload checksum during write and SHA-256 for manifest evidence.
6.  Close and fsync according to generator durability setting, then atomically publish each file.
7.  Write the canonical manifest last, after every file descriptor and digest is known.
8.  Provide a verify command that re-reads headers, counts records, checks ranges, and optionally recalculates full digests.

The generator itself is a benchmarkable component. Report generation throughput separately from Forge execution throughput, and never include dataset-generation time in task-processing results unless explicitly studying end-to-end provisioning.

## 91. Partition Index and Boundary Validation

Fixed-size records allow partition offsets to be calculated safely: byte_start = header_bytes + record_start × record_bytes. Use checked arithmetic and verify byte_start + record_count × record_bytes does not overflow or exceed file size.

- Planner tests cover empty datasets, one record, exact partition multiple, final short partition, multiple files, maximum values, and arithmetic overflow.
- A partition plan digest hashes the ordered canonical descriptors so recovery and workers can detect accidental changes.
- Workers recalculate or validate byte boundaries from logical indices instead of trusting an arbitrary byte range blindly.
- A future variable-length format requires an explicit index; do not reuse fixed-record assumptions silently.

## 92. Artifact Store Layout

    artifacts/
      datasets/
        <dataset-id>/
          manifest.json
          part-00000.fev
      runs/
        <run-id>/
          accepted-run.json
          plan.json
          attempts/
            <task-id>/<attempt-id>/
              output.tmp
              output.staged
              attempt-result.json
          committed/
            <task-id>/result.bin
            <task-id>/result.json
          final/
            result.bin
            result.json
          checkpoints/
            checkpoint-000001.json
          diagnostics/
            <bundle-id>/...
      evidence/
        benchmarks/<release>/<study>/...

The exact directory names are less important than root confinement, unique staging paths, immutable committed paths, and a manifest that records every artifact reference. Do not infer task state by scanning directory names; metadata is authoritative.

## 93. Artifact Descriptor

    @dataclass(frozen=True)
    class ArtifactDescriptor:
        schema: str
        uri: str
        byte_size: int
        sha256: str
        logical_records: int | None
        media_type: str
        created_by_attempt: str | None
        content_schema: str
        canonical_digest: str | None

- uri is resolved through an artifact store adapter and is not accepted as an arbitrary OS path from the network.
- sha256 identifies exact bytes. canonical_digest identifies normalized logical content when byte representation may differ.
- created_by_attempt is evidence, not part of canonical result equivalence.
- media_type and content_schema prevent a merge from interpreting arbitrary bytes as a partition result.
- The descriptor is immutable after publication. Corrections create a new artifact and metadata transition.

## 94. Staging and Atomic Publication

**Table 38 --- Artifact staging and publication sequence.**

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Step                   Filesystem baseline                                                                 Failure handling
  ---------------------- ----------------------------------------------------------------------------------- -----------------------------------------------------------------------
  Create                 mkdir/open with exclusive flags under attempt path                                  Existing conflicting path is an error or prior-attempt recovery case.

  Write                  Stream to output.tmp with hard byte limit                                           Short write or exception leaves incomplete marker.

  Flush                  Flush language buffers and fsync file if durability mode requires                   Report storage failure; do not stage.

  Finalize               Rename output.tmp to output.staged within same directory                            Atomic within documented filesystem assumption.

  Manifest               Write attempt-result.tmp, fsync, rename to JSON manifest                            Missing finalized manifest means attempt is incomplete.

  Verify                 Coordinator checks root, file type, size, and digest                                Mismatch quarantines artifact and rejects commit.

  Publish                Rename/copy-link to immutable committed path or record staged URI transactionally   Metadata transaction decides visibility.

  Directory durability   Optional fsync parent directories                                                   Durability mode states whether sudden power loss is in scope.
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 95. Partition Result Schema

The first kernel should produce a compact, independently verifiable result. A good example is per-stream count, sum, minimum, maximum, and first/last sequence for selected event types.

    {
      "schema": "forge.partition_result.v1",
      "run_id": "...",
      "task_id": "...",
      "partition_ordinal": 17,
      "input": {
        "file_id": 0,
        "record_start": 17000000,
        "record_count": 1000000
      },
      "kernel": "telemetry.stats_by_stream@1.0.0",
      "records_read": 1000000,
      "records_selected": 249812,
      "groups": [
        {"stream_id": 0, "count": 61, "sum": 1493,
         "min": -87, "max": 132, "first_sequence": 17000102,
         "last_sequence": 17999832}
      ],
      "canonical_digest": "..."
    }

Attempt ID, worker ID, duration, and resource metrics belong in the attempt manifest rather than the canonical logical result. This separation lets retries and worker counts change without changing result equivalence.

## 96. Checkpoint Manifest

A checkpoint is an immutable summary of durable progress, not a second source of truth. It can accelerate inspection or allow export/import, but the metadata database remains authoritative for the running coordinator.

**Table 39 --- Checkpoint manifest fields.**

  ----------------------------------------------------------------------------------------------------------
  Field                                                   Purpose
  ------------------------------------------------------- --------------------------------------------------
  schema/version                                          Reject incompatible checkpoint readers.

  run_id and manifest digest                              Bind checkpoint to one immutable run definition.

  metadata event sequence or database snapshot identity   State the consistency point.

  committed task ordinals and artifact descriptors        Identify reusable durable work.

  terminal task failures and cancellation state           Preserve outcome context.

  merge state and final artifact if present               Support idempotent finalization.

  created timestamp and Forge version                     Diagnostic provenance.

  checkpoint digest                                       Detect accidental modification.
  ----------------------------------------------------------------------------------------------------------

## 97. Metadata Schema Overview

**Table 40 --- Metadata database tables.**

  -------------------------------------------------------------------------------------------------------------------------------------------
  Table                          Key rows and constraints
  ------------------------------ ------------------------------------------------------------------------------------------------------------
  runs                           run_id PK; manifest digest unique with optional request scope; state CHECK; final artifact FK; counters.

  partitions                     run_id + ordinal unique; immutable boundaries; plan digest.

  tasks                          task_id PK; run/stage/partition unique; state; fencing_generation; committed_attempt FK; retry_not_before.

  attempts                       attempt_id PK; task FK; worker/session; generation; state; timestamps; error; artifact FK.

  leases                         attempt FK unique for active generation; worker; issued/expiry; state.

  workers                        worker_id and session generation; capabilities digest; state; last seen.

  artifacts                      artifact_id or digest; URI; size; exact-byte digest; schema; publication state.

  events                         monotonic event sequence; entity; before/after; type; actor; bounded details.

  client_requests                client namespace + request ID unique; canonical request digest; run FK.

  schema_migrations              applied migration ID, checksum, timestamp, application version.
  -------------------------------------------------------------------------------------------------------------------------------------------

## 98. Database Constraints Worth Enforcing

- Unique run request key per client namespace.
- Unique partition ordinal per run and unique task per run/stage/partition.
- At most one committed attempt reference per task through one column and foreign key.
- Attempt generation and task fencing generation are non-negative and internally consistent through transition code and checks.
- Terminal states require terminal timestamps; committed task requires committed_attempt_id and digest.
- Artifact digest and URI cannot be null when publication state is VERIFIED or COMMITTED.
- Foreign-key deletion is restricted for historical entities; cleanup removes bytes, not evidence rows casually.
- Events are append-only from the application perspective.

## 99. Integrity Modes

**Table 41 --- Artifact integrity modes.**

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Mode            Dataset checks                                                                                     Result checks                                        Intended use
  --------------- -------------------------------------------------------------------------------------------------- ---------------------------------------------------- --------------------------------------
  fast            Validate header, size, partition bounds; trust registered manifest hash                            Check size and streaming digest produced by writer   Development iteration.

  standard        Verify file SHA-256 once per worker cache or run                                                   Coordinator recalculates staged result SHA-256       Public demos and correctness tests.

  strict          Recalculate all dataset digests at run start or registration and verify per access as configured   Recalculate committed artifacts during recovery      Fault-injection and integrity study.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Benchmark reports must state the integrity mode because hashing can materially affect throughput. Never compare a fast-mode result against a strict-mode result without separating the costs.

## 100. Garbage Collection and Retention

- A GC scan first obtains durable references and terminal state; it never deletes a path solely because its name looks temporary.
- Incomplete attempt files may be deleted after a grace period if no active attempt references them.
- Losing staged artifacts may be retained for a short diagnostic period and then removed idempotently.
- Committed artifacts are retained while any run, checkpoint, evidence bundle, or exported manifest references them.
- Diagnostics and benchmark evidence have explicit retention independent of runtime staging cleanup.
- GC writes a report of candidates, exclusions, deleted bytes, failures, and dry-run mode.
- Use a two-pass or tombstone approach if interruption during deletion would make auditability difficult.

## 101. Storage Corruption and Failure Policy

**Table 42 --- Storage corruption and failure policy.**

  ------------------------------------------------------------------------------------------------------------------------------------------------------
  Observation                                       Policy
  ------------------------------------------------- ----------------------------------------------------------------------------------------------------
  Dataset header invalid before execution           Fail task/run as deterministic input validation error.

  Dataset checksum differs from accepted manifest   Fail closed; dataset identity is broken.

  Staged output digest mismatch                     Reject commit, quarantine artifact, classify worker/storage failure.

  Committed artifact missing at recovery            Mark run corrupt/failed and preserve metadata; never silently recompute under same historical run.

  Metadata database integrity check fails           Refuse readiness, copy evidence safely, require manual or scripted recovery.

  Disk full during staging                          Fail attempt retryably only if another attempt can use available storage; expose capacity alarm.

  Atomic rename crosses filesystems                 Reject configuration or use explicit copy-verify-publish adapter; do not assume atomicity.
  ------------------------------------------------------------------------------------------------------------------------------------------------------

## 102. Storage Acceptance Tests

**Table 43 --- Storage acceptance tests.**

  ---------------------------------------------------------------------------------------------------------------------------------------
  Test ID                        Acceptance case
  ------------------------------ --------------------------------------------------------------------------------------------------------
  STORE-001                      Generator emits byte-identical files and manifest for a fixed seed and version.

  STORE-002                      Header parser rejects bad magic, unsupported version, short header, invalid record size, and overflow.

  STORE-003                      Partition boundaries cover each declared record exactly once.

  STORE-004                      Attempt writers cannot collide or escape root.

  STORE-005                      Crash before finalize leaves no valid staged manifest.

  STORE-006                      Digest mismatch prevents commit.

  STORE-007                      Committed artifact survives coordinator restart and verifies.

  STORE-008                      Missing committed artifact is detected and not silently recomputed.

  STORE-009                      GC dry run lists only unreferenced eligible artifacts.

  STORE-010                      GC interruption is idempotent and never removes committed bytes.

  STORE-011                      Strict and fast integrity modes produce the same logical result.

  STORE-012                      Database constraints reject intentionally invalid rows.
  ---------------------------------------------------------------------------------------------------------------------------------------
