"""Turn a validated dataset manifest + experiment manifest into run-bound partitions
(§274 Week 4; closes the gap left in `forge.datasets.partitioning`'s Week 3 module
docstring, where `partition_seed` was `None` because no run seed existed yet).

Single-file datasets only: every dataset this generator (`forge.datasets.generator`)
produces has exactly one file, and Week 4's reference engine only needs to run
against those. A multi-file dataset would need this to plan across files in a
declared order — deferred until something actually generates one.
"""

from __future__ import annotations

import hashlib

from forge.datasets.manifest import DatasetManifest
from forge.datasets.partitioning import plan_dataset_partitions
from forge.domain.descriptors import PartitionDescriptor
from forge.domain.identifiers import DatasetId
from forge.domain.manifests import ExperimentManifest


class PlanningError(ValueError):
    """Raised when a dataset manifest and experiment manifest cannot be planned
    together — e.g. a digest mismatch or an unsupported dataset shape."""


def derive_partition_seed(run_seed: int, stage: str, partition_id: str) -> int:
    """§25: "a documented cryptographic or stable hash of run seed, stage, and
    partition ID; never use Python built-in hash" — `hash()` is salted per-process
    (`PYTHONHASHSEED`), so it would silently break reproducibility across processes
    or restarts. sha256 has no such issue and is already this project's one hash
    algorithm (§34)."""
    payload = f"{run_seed}:{stage}:{partition_id}".encode()
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big")


def plan_run_partitions(
    dataset_manifest: DatasetManifest,
    experiment_manifest: ExperimentManifest,
    *,
    run_seed: int,
    stage: str = "map",
) -> list[PartitionDescriptor]:
    """Validate the experiment's declared dataset digest against the actual dataset
    manifest (closing §17's "reject... inconsistent dataset digests" requirement,
    which Week 2 could only document as deferred — this is the first place both
    manifests exist together), then plan partitions with a real `partition_seed`."""
    if dataset_manifest.dataset_id != experiment_manifest.dataset.dataset_id:
        raise PlanningError(
            f"experiment references dataset_id {experiment_manifest.dataset.dataset_id!r}, "
            f"but the loaded dataset manifest is {dataset_manifest.dataset_id!r}"
        )
    if dataset_manifest.content_sha256 != experiment_manifest.dataset.content_sha256:
        raise PlanningError(
            f"experiment's declared dataset content_sha256 "
            f"({experiment_manifest.dataset.content_sha256}) does not match the loaded "
            f"dataset manifest's ({dataset_manifest.content_sha256})"
        )
    if len(dataset_manifest.files) != 1:
        raise PlanningError(
            f"only single-file datasets are supported, got {len(dataset_manifest.files)} files"
        )

    file_entry = dataset_manifest.files[0]
    dataset_only_partitions = plan_dataset_partitions(
        dataset_id=DatasetId(dataset_manifest.dataset_id),
        file_id=file_entry.relative_path,
        record_count=file_entry.record_count,
        target_records_per_partition=experiment_manifest.partitioning.target_records_per_task,
        record_bytes=dataset_manifest.record_schema.record_bytes,
    )

    return [
        PartitionDescriptor(
            dataset_id=partition.dataset_id,
            partition_id=partition.partition_id,
            ordinal=partition.ordinal,
            file_id=partition.file_id,
            record_start=partition.record_start,
            record_count=partition.record_count,
            partition_seed=derive_partition_seed(run_seed, stage, partition.partition_id),
            byte_start=partition.byte_start,
            byte_length=partition.byte_length,
            expected_input_digest=partition.expected_input_digest,
        )
        for partition in dataset_only_partitions
    ]
