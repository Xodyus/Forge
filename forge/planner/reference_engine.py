"""Single-process reference/oracle engine (§274 Week 4, Gate A).

"Deliberately simple sequential implementation used as a correctness oracle"
(glossary, `docs/spec/appendix-l.md` §427) — plan, execute each partition, stage its
result as a local file, merge in canonical ordinal order, publish a result manifest.
There is no coordinator, no leases, no attempts yet (Week 5+); "attempt-like local
outputs" here just means writing each partition's result to its own file before
merging, the same staging-then-combining shape §27 describes, without any of the
durable-metadata machinery that makes it safe under concurrency and crashes.

§274's normalization requirement — "nondecreasing timestamps or paths do not affect
the semantic result digest" — falls out of the ordering here rather than needing a
separate normalization pass: `canonical_result_digest` is computed from `final_result`
bytes alone, before `ReferenceResultManifest` (which carries the wall-clock
`created_utc`) is even constructed. There's nothing non-deterministic left for the
digest to depend on.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from pydantic import BaseModel, ConfigDict, Field

from forge.datasets.atomic import write_atomic
from forge.datasets.manifest import DatasetManifest
from forge.datasets.reader import DatasetFileReader
from forge.domain.digests import Digest
from forge.domain.manifests import ExperimentManifest
from forge.kernels.base import KernelRegistry
from forge.planner.plan import plan_run_partitions

RESULT_MANIFEST_SCHEMA_NAME = "forge.reference-result-manifest"
RESULT_MANIFEST_SCHEMA_VERSION = 1


class ReferenceResultManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_name: str = Field(alias="schema", default=RESULT_MANIFEST_SCHEMA_NAME)
    schema_version: int = RESULT_MANIFEST_SCHEMA_VERSION
    dataset_id: str
    kernel_id: str
    kernel_version: str
    run_seed: int
    partition_count: int
    canonical_result_digest: str
    created_utc: datetime


def _writer_for(data: bytes) -> Callable[[BinaryIO], None]:
    def _write(handle: BinaryIO) -> None:
        handle.write(data)

    return _write


def run_reference_experiment(
    dataset_file: Path,
    dataset_manifest: DatasetManifest,
    experiment_manifest: ExperimentManifest,
    kernel_registry: KernelRegistry,
    *,
    run_seed: int,
    output_dir: Path,
) -> ReferenceResultManifest:
    kernel = kernel_registry.resolve(
        kernel_id=experiment_manifest.kernel.kernel_id,
        kernel_version=experiment_manifest.kernel.kernel_version,
        engine=experiment_manifest.kernel.engine,
    )
    # §20: "Parameter validation runs before tasks are created so an invalid
    # experiment fails early and durably" — before any partition executes.
    kernel.validate_parameters(experiment_manifest.kernel.parameters)

    partitions = plan_run_partitions(dataset_manifest, experiment_manifest, run_seed=run_seed)

    reader = DatasetFileReader.open(dataset_file)
    reader.verify_payload_digest()

    partitions_dir = output_dir / "partitions"
    for partition in partitions:
        records = list(
            reader.read_records(
                record_start=partition.record_start, record_count=partition.record_count
            )
        )
        partial_result = kernel.execute_partition(records, experiment_manifest.kernel.parameters)
        write_atomic(
            partitions_dir / f"{partition.partition_id}.result", _writer_for(partial_result)
        )

    # Re-read the staged outputs rather than reusing what's still in memory: the
    # merge step operates on what was actually published, in canonical ordinal
    # order (§24) — not on completion order, which for a sequential loop happens to
    # be the same thing, but the read-back keeps that an explicit property of the
    # merge step rather than an accident of this loop's structure.
    ordered_partial_results = [
        (partitions_dir / f"{partition.partition_id}.result").read_bytes()
        for partition in partitions
    ]

    final_result = kernel.merge(ordered_partial_results, experiment_manifest.kernel.parameters)
    canonical_result_digest = Digest.of_bytes(final_result)

    write_atomic(output_dir / "result.bin", _writer_for(final_result))

    manifest = ReferenceResultManifest(
        dataset_id=dataset_manifest.dataset_id,
        kernel_id=kernel.kernel_id,
        kernel_version=kernel.kernel_version,
        run_seed=run_seed,
        partition_count=len(partitions),
        canonical_result_digest=canonical_result_digest.hex_value,
        created_utc=datetime.now(UTC),
    )
    manifest_json = manifest.model_dump_json(by_alias=True, indent=2)
    write_atomic(output_dir / "result-manifest.json", _writer_for(manifest_json.encode("utf-8")))

    return manifest
