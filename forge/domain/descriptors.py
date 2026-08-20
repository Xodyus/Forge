"""Immutable value objects describing partitions, kernels, artifacts, and leases.

Field sets are transcribed from §19 Table 11 (partition descriptor) and §16 Table 10
(identifier rules that shape the kernel/artifact/lease fields), extended beyond
Appendix B §353's trimmed skeleton to include every field those tables require.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True, slots=True)
class PartitionDescriptor:
    """A deterministic logical slice of a dataset (§19 Table 11).

    ``partition_seed`` is a *run*-level value — §19 defines it as "computed from run
    seed and partition identity" — so it is ``None`` for the dataset-only partition
    index :func:`forge.datasets.partitioning.plan_dataset_partitions` produces (Week
    3), and only gets filled in once a run/experiment seed exists to derive it from
    (``forge.planner``, Week 4).
    """

    dataset_id: DatasetId
    partition_id: PartitionId
    ordinal: int
    file_id: str
    record_start: int
    record_count: int
    partition_seed: int | None = None
    byte_start: int | None = None
    byte_length: int | None = None
    expected_input_digest: Digest | None = None

    def __post_init__(self) -> None:
        if self.ordinal < 0:
            raise ValueError("ordinal must be non-negative")
        if self.record_start < 0:
            raise ValueError("record_start must be non-negative")
        if self.record_count < 0:
            raise ValueError("record_count must be non-negative")
        if (self.byte_start is None) != (self.byte_length is None):
            raise ValueError("byte_start and byte_length must be set together")
        if self.byte_start is not None and self.byte_start < 0:
            raise ValueError("byte_start must be non-negative")
        if self.byte_length is not None and self.byte_length < 0:
            raise ValueError("byte_length must be non-negative")
        if self.record_count == 0 and self.byte_length:
            raise ValueError("empty partition cannot claim a nonzero byte span")


@dataclass(frozen=True, slots=True)
class KernelDescriptor:
    """A versioned, registered computation reference (§20)."""

    kernel_id: str
    kernel_version: str
    parameter_schema_version: int
    parameters_canonical_json: bytes
    engine: str  # "python" or "cpp"

    def __post_init__(self) -> None:
        if self.engine not in ("python", "cpp"):
            raise ValueError(f"unsupported engine: {self.engine!r}")
        if self.parameter_schema_version < 1:
            raise ValueError("parameter_schema_version must be positive")
        if not self.kernel_id or not self.kernel_version:
            raise ValueError("kernel_id and kernel_version must be non-empty")


@dataclass(frozen=True, slots=True)
class ArtifactDescriptor:
    """An immutable output reference, staged or committed (§27, Appendix B §353)."""

    artifact_id: ArtifactId
    attempt_id: AttemptId
    relative_path: Path
    byte_count: int
    content_digest: Digest
    schema_id: str
    schema_version: int

    def __post_init__(self) -> None:
        if self.relative_path.is_absolute():
            raise ValueError("artifact paths must be relative")
        if ".." in self.relative_path.parts:
            raise ValueError("artifact path traversal is forbidden")
        if self.byte_count < 0:
            raise ValueError("artifact byte count must be non-negative")
        if self.schema_version < 1:
            raise ValueError("schema_version must be positive")


@dataclass(frozen=True, slots=True)
class LeaseGrant:
    """A time-limited authorization for one worker attempt (§22)."""

    run_id: RunId
    task_id: TaskId
    attempt_id: AttemptId
    worker_id: WorkerId
    fencing_epoch: int
    deadline_monotonic_ns: int
    partition: PartitionDescriptor
    kernel: KernelDescriptor

    def __post_init__(self) -> None:
        if self.fencing_epoch <= 0:
            raise ValueError("fencing epoch must be positive")
        if self.deadline_monotonic_ns <= 0:
            raise ValueError("lease deadline must be positive")
