from pathlib import Path
from uuid import uuid4

import pytest
from forge.domain.descriptors import (
    ArtifactDescriptor,
    KernelDescriptor,
    LeaseGrant,
    PartitionDescriptor,
)
from forge.domain.digests import Digest
from forge.domain.identifiers import (
    ArtifactId,
    AttemptId,
    DatasetId,
    PartitionId,
    RunId,
    TaskId,
    WorkerId,
)

SOME_DIGEST = Digest.of_bytes(b"payload")


def _partition(**overrides: object) -> PartitionDescriptor:
    fields: dict[str, object] = dict(
        dataset_id=DatasetId("ds-1"),
        partition_id=PartitionId("p-0"),
        ordinal=0,
        file_id="events-00000.forge",
        record_start=0,
        record_count=1_000,
        partition_seed=42,
    )
    fields.update(overrides)
    return PartitionDescriptor(**fields)  # type: ignore[arg-type]


def test_valid_partition_descriptor_constructs() -> None:
    partition = _partition()
    assert partition.record_count == 1_000


@pytest.mark.parametrize(
    "overrides",
    [
        {"ordinal": -1},
        {"record_start": -1},
        {"record_count": -1},
        {"byte_start": 0},  # byte_length missing
        {"byte_length": 0},  # byte_start missing
        {"byte_start": -1, "byte_length": 10},
        {"byte_start": 10, "byte_length": -1},
        {"record_count": 0, "byte_start": 0, "byte_length": 10},
    ],
)
def test_partition_descriptor_rejects_invalid_values(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _partition(**overrides)


def test_partition_descriptor_allows_paired_byte_range() -> None:
    partition = _partition(byte_start=0, byte_length=32_000)
    assert partition.byte_length == 32_000


def test_kernel_descriptor_rejects_unknown_engine() -> None:
    with pytest.raises(ValueError, match="engine"):
        KernelDescriptor(
            kernel_id="forge.count",
            kernel_version="1.0.0",
            parameter_schema_version=1,
            parameters_canonical_json=b"{}",
            engine="rust",
        )


def test_kernel_descriptor_rejects_non_positive_schema_version() -> None:
    with pytest.raises(ValueError, match="parameter_schema_version"):
        KernelDescriptor(
            kernel_id="forge.count",
            kernel_version="1.0.0",
            parameter_schema_version=0,
            parameters_canonical_json=b"{}",
            engine="python",
        )


def _artifact(**overrides: object) -> ArtifactDescriptor:
    fields: dict[str, object] = dict(
        artifact_id=ArtifactId(uuid4()),
        attempt_id=AttemptId(uuid4()),
        relative_path=Path("staged/attempt-1/output.bin"),
        byte_count=128,
        content_digest=SOME_DIGEST,
        schema_id="forge.partition_result.v1",
        schema_version=1,
    )
    fields.update(overrides)
    return ArtifactDescriptor(**fields)  # type: ignore[arg-type]


def test_artifact_descriptor_rejects_absolute_path() -> None:
    absolute = Path(Path.cwd().anchor) / "etc" / "passwd"
    with pytest.raises(ValueError, match="relative"):
        _artifact(relative_path=absolute)


def test_artifact_descriptor_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="traversal"):
        _artifact(relative_path=Path("../../etc/passwd"))


def test_artifact_descriptor_rejects_negative_byte_count() -> None:
    with pytest.raises(ValueError, match="byte count"):
        _artifact(byte_count=-1)


def test_lease_grant_rejects_non_positive_fencing_epoch() -> None:
    with pytest.raises(ValueError, match="fencing epoch"):
        LeaseGrant(
            run_id=RunId(uuid4()),
            task_id=TaskId(uuid4()),
            attempt_id=AttemptId(uuid4()),
            worker_id=WorkerId(uuid4()),
            fencing_epoch=0,
            deadline_monotonic_ns=1,
            partition=_partition(),
            kernel=KernelDescriptor(
                kernel_id="forge.count",
                kernel_version="1.0.0",
                parameter_schema_version=1,
                parameters_canonical_json=b"{}",
                engine="python",
            ),
        )


def test_lease_grant_rejects_non_positive_deadline() -> None:
    with pytest.raises(ValueError, match="deadline"):
        LeaseGrant(
            run_id=RunId(uuid4()),
            task_id=TaskId(uuid4()),
            attempt_id=AttemptId(uuid4()),
            worker_id=WorkerId(uuid4()),
            fencing_epoch=1,
            deadline_monotonic_ns=0,
            partition=_partition(),
            kernel=KernelDescriptor(
                kernel_id="forge.count",
                kernel_version="1.0.0",
                parameter_schema_version=1,
                parameters_canonical_json=b"{}",
                engine="python",
            ),
        )
