# Appendix C - Dataset and Manifest Formats

## 357. Synthetic Event Record Layout

**Table 132 --- Thirty-two-byte synthetic event record.**

  ---------------------------------------------------------------------------------------------------------------------
  Offset          Bytes           Field           Type and rule
  --------------- --------------- --------------- ---------------------------------------------------------------------
  0               8               timestamp_ns    little-endian unsigned 64-bit; nondecreasing within generated shard

  8               4               instrument_id   little-endian unsigned 32-bit

  12              1               event_type      unsigned 8-bit registered event code

  13              1               flags           unsigned 8-bit; unknown required flags rejected

  14              2               reserved        must be zero in schema v1

  16              8               value_i64       little-endian signed 64-bit payload value

  24              4               quantity        little-endian unsigned 32-bit

  28              4               sequence        little-endian unsigned 32-bit source sequence
  ---------------------------------------------------------------------------------------------------------------------

## 358. Dataset File Header Layout

**Table 133 --- Illustrative 128-byte dataset header.**

  ------------------------------------------------------------------------------------------------------
  Offset          Bytes           Field             Rule
  --------------- --------------- ----------------- ----------------------------------------------------
  0               8               magic             ASCII `FORGEV1\0` or finalized eight-byte constant

  8               2               header_version    little-endian unsigned 16-bit

  10              2               record_schema     little-endian unsigned 16-bit

  12              4               header_bytes      total fixed and extension header bytes

  16              8               record_count      unsigned 64-bit

  24              4               record_bytes      must equal 32 for schema v1

  28              4               flags             feature and checksum policy bits

  32              32              payload_sha256    digest of record payload bytes

  64              32              manifest_sha256   digest of canonical generator/file metadata

  96              32              reserved          zero until assigned by a compatible version
  ------------------------------------------------------------------------------------------------------

## 359. Dataset Manifest Example

    {
      "schema": "forge.dataset-manifest",
      "schema_version": 1,
      "dataset_id": "synthetic-orders-v1-seed-17",
      "created_by": {
        "generator_id": "forge.synthetic-events",
        "generator_version": "1.0.0",
        "seed": 17
      },
      "record_schema": {
        "id": "forge.event.fixed32",
        "version": 1,
        "record_bytes": 32,
        "byte_order": "little"
      },
      "files": [
        {
          "relative_path": "data/events-00000.forge",
          "byte_count": 32000128,
          "record_count": 1000000,
          "sha256": "<file digest>",
          "payload_sha256": "<payload digest>"
        }
      ],
      "generation": {
        "timestamp_start_ns": 0,
        "timestamp_step_distribution": "uniform:1..1000",
        "instrument_count": 128,
        "event_type_weights": {"1": 0.60, "2": 0.25, "3": 0.15},
        "value_distribution": "normal:mean=0,stddev=100000",
        "quantity_distribution": "lognormal:parameters=<frozen>"
      },
      "content_sha256": "<digest of canonical file descriptors>"
    }

## 360. Experiment Manifest Example

    {
      "schema": "forge.experiment-manifest",
      "schema_version": 1,
      "experiment_id": "instrument-stats-example",
      "dataset": {
        "dataset_id": "synthetic-orders-v1-seed-17",
        "content_sha256": "<dataset content digest>"
      },
      "partitioning": {
        "policy": "contiguous-record-ranges",
        "policy_version": 1,
        "target_records_per_task": 250000
      },
      "kernel": {
        "kernel_id": "forge.instrument-stats",
        "kernel_version": "1.0.0",
        "engine": "python",
        "parameter_schema_version": 1,
        "parameters": {
          "include_event_types": [1, 2, 3]
        }
      },
      "execution": {
        "max_attempts_per_task": 3,
        "attempt_timeout_seconds": 120,
        "lease_seconds": 30,
        "heartbeat_seconds": 5,
        "max_parallel_tasks": 8
      },
      "result": {
        "schema_id": "forge.instrument-stats-result",
        "schema_version": 1,
        "canonical_merge": "instrument-id-ascending"
      }
    }

## 361. Safe Atomic File Publication Helper

    from __future__ import annotations

    import hashlib
    import os
    from pathlib import Path
    from typing import BinaryIO, Callable
    from uuid import uuid4

    Writer = Callable[[BinaryIO], None]


    def write_atomic(
        destination: Path,
        writer: Writer,
        *,
        mode: int = 0o640,
    ) -> tuple[int, str]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            f".{destination.name}.{uuid4().hex}.tmp"
        )
        digest = hashlib.sha256()
        byte_count = 0

        class DigestingWriter:
            def __init__(self, raw: BinaryIO) -> None:
                self.raw = raw

            def write(self, data: bytes) -> int:
                nonlocal byte_count
                written = self.raw.write(data)
                if written != len(data):
                    raise OSError("short buffered file write")
                digest.update(data)
                byte_count += written
                return written

            def flush(self) -> None:
                self.raw.flush()

        try:
            fd = os.open(
                temporary,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                mode,
            )
            with os.fdopen(fd, "wb", buffering=1024 * 1024) as raw:
                wrapped = DigestingWriter(raw)
                writer(wrapped)  # type: ignore[arg-type]
                wrapped.flush()
                os.fsync(raw.fileno())

            os.replace(temporary, destination)
            directory_fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

        return byte_count, digest.hexdigest()

## 362. Dataset Validation Checklist

- Resolve every file beneath an approved dataset root and reject absolute paths, `..`, unexpected symlinks, and non-regular files.
- Check header magic and minimum size before parsing version-dependent fields.
- Use checked arithmetic for header bytes plus record count times record bytes; reject overflow and mismatch with actual file size.
- Reject unsupported schema versions and unknown required flags before reading payload.
- Verify file and payload digests according to explicit validation mode; record whether validation was full or sampled.
- Validate partition byte offsets and lengths against header and record alignment.
- Treat zero records and empty files deliberately; do not accidentally divide by zero or create phantom tasks.
- Use deterministic ordering of files and partitions independent of filesystem enumeration.
- Do not memory-map a path before all basic size and schema checks are complete.
- Record dataset content identity in every run manifest and attempt descriptor.
