# Appendix B - Canonical Python Domain Model Skeleton

## 352. Purpose and Caveat

The code in this appendix is a design skeleton, not a drop-in complete implementation. It demonstrates strong types, immutable descriptors, explicit states, and validation boundaries. The final repository should split types by responsibility, add schema serialization, use stable error classes, enforce version compatibility, and test every transition. Do not copy a skeleton into production without filling those gaps.

## 353. Identifiers, Enums, and Immutable Descriptors

    from __future__ import annotations

    from dataclasses import dataclass
    from enum import Enum, IntEnum
    from pathlib import Path
    from typing import NewType
    from uuid import UUID

    RunId = NewType("RunId", UUID)
    TaskId = NewType("TaskId", UUID)
    AttemptId = NewType("AttemptId", UUID)
    WorkerId = NewType("WorkerId", UUID)
    ArtifactId = NewType("ArtifactId", UUID)


    class RunState(str, Enum):
        PLANNING = "planning"
        RUNNING = "running"
        CANCELLING = "cancelling"
        SUCCEEDED = "succeeded"
        FAILED = "failed"
        CANCELLED = "cancelled"


    class TaskState(str, Enum):
        PENDING = "pending"
        LEASED = "leased"
        COMMITTED = "committed"
        FAILED = "failed"
        CANCELLED = "cancelled"


    class AttemptState(str, Enum):
        ASSIGNED = "assigned"
        RUNNING = "running"
        STAGED = "staged"
        COMMITTED = "committed"
        FAILED = "failed"
        EXPIRED = "expired"
        CANCELLED = "cancelled"
        REJECTED_STALE = "rejected_stale"


    class ErrorClass(str, Enum):
        VALIDATION = "validation"
        KERNEL = "kernel"
        TIMEOUT = "timeout"
        CANCELLED = "cancelled"
        WORKER_LOST = "worker_lost"
        STORAGE = "storage"
        PROTOCOL = "protocol"
        INTERNAL = "internal"


    class Side(IntEnum):
        BUY = 1
        SELL = 2


    @dataclass(frozen=True, slots=True)
    class Digest:
        algorithm: str
        hex_value: str

        def __post_init__(self) -> None:
            if self.algorithm != "sha256":
                raise ValueError("only sha256 is supported in schema v1")
            if len(self.hex_value) != 64:
                raise ValueError("invalid sha256 digest length")
            int(self.hex_value, 16)


    @dataclass(frozen=True, slots=True)
    class PartitionDescriptor:
        dataset_id: str
        partition_id: str
        file_index: int
        byte_offset: int
        byte_length: int
        first_record: int
        record_count: int
        content_digest: Digest

        def __post_init__(self) -> None:
            values = (
                self.file_index,
                self.byte_offset,
                self.byte_length,
                self.first_record,
                self.record_count,
            )
            if any(value < 0 for value in values):
                raise ValueError("partition values must be non-negative")
            if self.record_count == 0 and self.byte_length != 0:
                raise ValueError("empty partition cannot contain bytes")


    @dataclass(frozen=True, slots=True)
    class KernelDescriptor:
        kernel_id: str
        kernel_version: str
        parameter_schema_version: int
        parameters_canonical_json: bytes
        engine: str  # "python" or "cpp"


    @dataclass(frozen=True, slots=True)
    class LeaseGrant:
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


    @dataclass(frozen=True, slots=True)
    class ArtifactDescriptor:
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

## 354. Transition Validation

    from collections.abc import Mapping


    class IllegalTransition(RuntimeError):
        pass


    _ALLOWED_TASK_TRANSITIONS: Mapping[TaskState, frozenset[TaskState]] = {
        TaskState.PENDING: frozenset(
            {TaskState.LEASED, TaskState.CANCELLED, TaskState.FAILED}
        ),
        TaskState.LEASED: frozenset(
            {
                TaskState.PENDING,      # lease expired and retry remains
                TaskState.COMMITTED,
                TaskState.CANCELLED,
                TaskState.FAILED,
            }
        ),
        TaskState.COMMITTED: frozenset(),
        TaskState.FAILED: frozenset(),
        TaskState.CANCELLED: frozenset(),
    }


    def require_task_transition(
        current: TaskState,
        target: TaskState,
        *,
        allow_idempotent: bool = True,
    ) -> None:
        if current == target and allow_idempotent:
            return
        if target not in _ALLOWED_TASK_TRANSITIONS[current]:
            raise IllegalTransition(f"cannot transition task {current} -> {target}")

## 355. Domain Error Envelope

    from dataclasses import dataclass, field
    from typing import Any


    @dataclass(frozen=True, slots=True)
    class ErrorEnvelope:
        code: str
        classification: ErrorClass
        message: str
        retryable: bool
        details: dict[str, Any] = field(default_factory=dict)

        def public_dict(self) -> dict[str, Any]:
            """Return bounded, non-secret fields suitable for protocol or logs."""
            return {
                "code": self.code,
                "classification": self.classification.value,
                "message": self.message[:1_024],
                "retryable": self.retryable,
                "details": self.details,
            }

## 356. Kernel Registration Contract

    from collections.abc import Callable, Iterator, Mapping
    from dataclasses import dataclass
    from typing import Protocol, TypeAlias

    EventBatch: TypeAlias = memoryview
    PartialResult: TypeAlias = bytes
    KernelParameters: TypeAlias = Mapping[str, object]


    class Kernel(Protocol):
        kernel_id: str
        kernel_version: str
        result_schema_id: str
        result_schema_version: int

        def validate_parameters(
            self,
            parameters: KernelParameters,
        ) -> None: ...

        def execute_batches(
            self,
            batches: Iterator[EventBatch],
            parameters: KernelParameters,
        ) -> PartialResult: ...


    @dataclass(frozen=True, slots=True)
    class RegisteredKernel:
        descriptor: KernelDescriptor
        factory: Callable[[], Kernel]


    class KernelRegistry:
        def __init__(self) -> None:
            self._kernels: dict[tuple[str, str, str], RegisteredKernel] = {}

        def register(self, kernel: RegisteredKernel) -> None:
            key = (
                kernel.descriptor.kernel_id,
                kernel.descriptor.kernel_version,
                kernel.descriptor.engine,
            )
            if key in self._kernels:
                raise ValueError(f"duplicate kernel registration: {key}")
            self._kernels[key] = kernel

        def resolve(self, descriptor: KernelDescriptor) -> RegisteredKernel:
            key = (
                descriptor.kernel_id,
                descriptor.kernel_version,
                descriptor.engine,
            )
            try:
                return self._kernels[key]
            except KeyError as exc:
                raise LookupError(f"unsupported kernel: {key}") from exc
