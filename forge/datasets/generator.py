"""Seeded synthetic event generator (§273 Week 3, Appendix C §359 "generation").

Scope: a reference-scale generator, not a benchmark-scale one. Records are built in
memory and hashed once before the file is written, because the dataset file header
must carry `payload_sha256` (§358) — a digest of the very payload that follows it —
so the payload's digest has to be known before the header can be written. A
streaming, hash-then-rewrite-header variant would avoid the memory footprint at very
large record counts; that is a Week 17 (E10, benchmarking) concern, not a Week 3 one.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from forge.datasets.atomic import write_atomic
from forge.datasets.format import (
    DATASET_HEADER_BYTES,
    EVENT_RECORD_BYTES,
    DatasetFileHeader,
    EventRecord,
)
from forge.datasets.manifest import (
    DatasetFileEntry,
    DatasetGeneratorInfo,
    DatasetManifest,
    DatasetRecordSchema,
    compute_content_sha256,
)

GENERATOR_ID = "forge.synthetic-events"
GENERATOR_VERSION = "1.0.0"

_UNSIGNED_32_MAX = (1 << 32) - 1
_SIGNED_64_MIN = -(1 << 63)
_SIGNED_64_MAX = (1 << 63) - 1


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """Explicit, typed generation parameters. This is the source of truth for
    reproduction — the free-form `generation` block in the dataset manifest (Appendix
    C §359) is a human-readable rendering of these fields, not something a reader
    parses back into a config; regenerating a dataset only needs this config."""

    seed: int
    record_count: int
    timestamp_start_ns: int = 0
    timestamp_step_min: int = 1
    timestamp_step_max: int = 1_000
    instrument_count: int = 128
    event_type_weights: dict[int, float] = field(
        default_factory=lambda: {1: 0.60, 2: 0.25, 3: 0.15}
    )
    value_mean: float = 0.0
    value_stddev: float = 100_000.0
    quantity_log_mu: float = 3.0
    quantity_log_sigma: float = 1.0

    def __post_init__(self) -> None:
        if self.record_count < 0:
            raise ValueError("record_count must be non-negative")
        if self.timestamp_step_min < 1 or self.timestamp_step_max < self.timestamp_step_min:
            raise ValueError("timestamp step range must be positive and non-decreasing")
        if self.instrument_count < 1:
            raise ValueError("instrument_count must be positive")
        if not self.event_type_weights:
            raise ValueError("event_type_weights must be non-empty")
        if any(weight < 0 for weight in self.event_type_weights.values()):
            raise ValueError("event_type_weights must be non-negative")
        if sum(self.event_type_weights.values()) <= 0:
            raise ValueError("event_type_weights must sum to a positive value")


def _clamp(value: int, *, low: int, high: int) -> int:
    return max(low, min(high, value))


def generate_records(config: GeneratorConfig) -> Iterator[EventRecord]:
    """Deterministic given `config.seed`: a local `random.Random` instance, never
    process-global random state, so concurrent or repeated generation never
    interferes with itself (§25's determinism contract)."""
    rng = random.Random(config.seed)
    event_types = list(config.event_type_weights.keys())
    weights = list(config.event_type_weights.values())
    timestamp_ns = config.timestamp_start_ns

    for sequence in range(config.record_count):
        if sequence > 0:
            timestamp_ns += rng.randint(config.timestamp_step_min, config.timestamp_step_max)
        instrument_id = rng.randrange(config.instrument_count)
        event_type = rng.choices(event_types, weights=weights, k=1)[0]
        value_i64 = _clamp(
            round(rng.gauss(config.value_mean, config.value_stddev)),
            low=_SIGNED_64_MIN,
            high=_SIGNED_64_MAX,
        )
        quantity = _clamp(
            round(rng.lognormvariate(config.quantity_log_mu, config.quantity_log_sigma)),
            low=0,
            high=_UNSIGNED_32_MAX,
        )
        yield EventRecord(
            timestamp_ns=_clamp(timestamp_ns, low=0, high=(1 << 64) - 1),
            instrument_id=instrument_id,
            event_type=event_type,
            flags=0,
            value_i64=value_i64,
            quantity=quantity,
            sequence=sequence,
        )


def _generator_metadata_digest(
    *, generator_id: str, generator_version: str, seed: int, dataset_id: str, relative_path: str
) -> bytes:
    """Digest for the header's `manifest_sha256` field (§358) — a small, independent
    binding of the file to its generation identity. Computed before the full
    `DatasetManifest` exists, so it cannot be that manifest's own digest."""
    payload = json.dumps(
        {
            "generator_id": generator_id,
            "generator_version": generator_version,
            "seed": seed,
            "dataset_id": dataset_id,
            "relative_path": relative_path,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).digest()


def generate_dataset(
    output_dir: Path, config: GeneratorConfig, *, dataset_id: str
) -> DatasetManifest:
    """Write one dataset file plus its manifest under `output_dir`, atomically, and
    return the manifest. Layout matches Appendix C §359: `data/events-00000.forge`
    and `manifest.json` beside it."""
    records = list(generate_records(config))
    payload = b"".join(record.pack() for record in records)
    payload_sha256 = hashlib.sha256(payload).digest()

    relative_path = "data/events-00000.forge"
    header = DatasetFileHeader(
        header_version=1,
        record_schema=1,
        header_bytes=DATASET_HEADER_BYTES,
        record_count=config.record_count,
        record_bytes=EVENT_RECORD_BYTES,
        flags=0,
        payload_sha256=payload_sha256,
        manifest_sha256=_generator_metadata_digest(
            generator_id=GENERATOR_ID,
            generator_version=GENERATOR_VERSION,
            seed=config.seed,
            dataset_id=dataset_id,
            relative_path=relative_path,
        ),
    )

    def _write(handle: BinaryIO) -> None:
        handle.write(header.pack())
        handle.write(payload)

    byte_count, file_sha256 = write_atomic(output_dir / relative_path, _write)

    file_entry = DatasetFileEntry(
        relative_path=relative_path,
        byte_count=byte_count,
        record_count=config.record_count,
        sha256=file_sha256,
        payload_sha256=payload_sha256.hex(),
    )

    manifest = DatasetManifest(
        schema_name="forge.dataset-manifest",
        schema_version=1,
        dataset_id=dataset_id,
        created_by=DatasetGeneratorInfo(
            generator_id=GENERATOR_ID, generator_version=GENERATOR_VERSION, seed=config.seed
        ),
        record_schema=DatasetRecordSchema(
            id="forge.event.fixed32",
            version=1,
            record_bytes=EVENT_RECORD_BYTES,
            byte_order="little",
        ),
        files=[file_entry],
        generation={
            "timestamp_start_ns": config.timestamp_start_ns,
            "timestamp_step_distribution": (
                f"uniform:{config.timestamp_step_min}..{config.timestamp_step_max}"
            ),
            "instrument_count": config.instrument_count,
            "event_type_weights": {str(k): v for k, v in config.event_type_weights.items()},
            "value_distribution": f"normal:mean={config.value_mean},stddev={config.value_stddev}",
            "quantity_distribution": (
                f"lognormal:mu={config.quantity_log_mu},sigma={config.quantity_log_sigma}"
            ),
        },
        content_sha256=compute_content_sha256([file_entry]),
    )

    manifest_json = manifest.model_dump_json(by_alias=True, indent=2)

    def _write_manifest(handle: BinaryIO) -> None:
        handle.write(manifest_json.encode("utf-8"))

    write_atomic(output_dir / "manifest.json", _write_manifest)

    return manifest
