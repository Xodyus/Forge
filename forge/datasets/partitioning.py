"""Deterministic dataset partition index (§273 Week 3, §19 partition contract).

Pure function, no I/O (§41's `plan_partitions(dataset, policy)` pure-core row) —
it only needs the record count a validated header/manifest already reported. It
produces `PartitionDescriptor`s with `partition_seed=None`: that field needs a run
seed, which doesn't exist at the dataset layer (see the note in
`forge.domain.descriptors.PartitionDescriptor`). `forge.planner` (Week 4) is what
turns this dataset-only index into run-bound partitions with a seed attached.
"""

from __future__ import annotations

from forge.domain.descriptors import PartitionDescriptor
from forge.domain.identifiers import DatasetId, PartitionId


def plan_dataset_partitions(
    *,
    dataset_id: DatasetId,
    file_id: str,
    record_count: int,
    target_records_per_partition: int,
    record_bytes: int,
) -> list[PartitionDescriptor]:
    """Contiguous, non-overlapping, dense-ordinal partitions covering
    `[0, record_count)` exactly once (INV-018). The last partition is short instead
    of empty or spilling over when `record_count` doesn't divide evenly."""
    if target_records_per_partition <= 0:
        raise ValueError("target_records_per_partition must be positive")
    if record_count < 0:
        raise ValueError("record_count must be non-negative")
    if record_bytes <= 0:
        raise ValueError("record_bytes must be positive")

    partitions: list[PartitionDescriptor] = []
    record_start = 0
    ordinal = 0
    while record_start < record_count:
        count = min(target_records_per_partition, record_count - record_start)
        partitions.append(
            PartitionDescriptor(
                dataset_id=dataset_id,
                partition_id=PartitionId(f"p-{ordinal:06d}"),
                ordinal=ordinal,
                file_id=file_id,
                record_start=record_start,
                record_count=count,
                byte_start=record_start * record_bytes,
                byte_length=count * record_bytes,
            )
        )
        record_start += count
        ordinal += 1

    return partitions
