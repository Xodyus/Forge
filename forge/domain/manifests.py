"""Experiment and run manifest schemas (§17, Appendix C §360).

The dataset manifest lives in :mod:`forge.datasets.manifest` instead — per §38's
component table, "manifest tools" for datasets are that package's job, while
experiment/run manifests are pure-core value objects consumed by both
``forge.planner`` and ``forge.coordinator`` and so belong here.

Every model rejects unknown fields (``extra="forbid"``) and validates its
``schema_version`` before any other field is interpreted (INV-020). What is
deliberately *not* validated here: whether a referenced ``kernel_id`` is registered,
and whether an experiment's ``dataset.content_sha256`` matches a real dataset
manifest. Both require a kernel registry / loaded dataset manifest that doesn't exist
until later weeks (E02, E04) — checking them here would be a stub that always
passes, not a test.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from forge.domain.invariants import InvariantViolationError, assert_schema_version_supported

Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

SUPPORTED_EXPERIMENT_SCHEMA_VERSIONS = (1,)
SUPPORTED_RUN_MANIFEST_MAJOR_VERSIONS = (1,)

_RUN_SCHEMA_VERSION_PATTERN = re.compile(r"^forge\.run\.v(?P<major>\d+)$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


# --- Experiment manifest (Appendix C §360) ----------------------------------------


class ExperimentDatasetRef(_StrictModel):
    dataset_id: str
    content_sha256: Sha256Hex


class ExperimentPartitioning(_StrictModel):
    policy: str
    policy_version: int = Field(ge=1)
    target_records_per_task: int = Field(gt=0)


class ExperimentKernelSpec(_StrictModel):
    kernel_id: str
    kernel_version: str
    engine: Literal["python", "cpp"]
    parameter_schema_version: int = Field(ge=1)
    parameters: dict[str, object] = Field(default_factory=dict)


class ExperimentExecution(_StrictModel):
    max_attempts_per_task: int = Field(ge=1)
    attempt_timeout_seconds: int = Field(gt=0)
    lease_seconds: int = Field(gt=0)
    heartbeat_seconds: int = Field(gt=0)
    max_parallel_tasks: int = Field(ge=1)


class ExperimentResult(_StrictModel):
    schema_id: str
    schema_version: int = Field(ge=1)
    canonical_merge: str


class ExperimentManifest(_StrictModel):
    schema_name: str = Field(alias="schema")
    schema_version: int
    experiment_id: str
    dataset: ExperimentDatasetRef
    partitioning: ExperimentPartitioning
    kernel: ExperimentKernelSpec
    execution: ExperimentExecution
    result: ExperimentResult

    @field_validator("schema_name")
    @classmethod
    def _check_schema_name(cls, value: str) -> str:
        if value != "forge.experiment-manifest":
            raise ValueError(f"unsupported schema {value!r}, expected forge.experiment-manifest")
        return value

    @field_validator("schema_version")
    @classmethod
    def _check_schema_version(cls, value: int) -> int:
        try:
            assert_schema_version_supported(
                value, SUPPORTED_EXPERIMENT_SCHEMA_VERSIONS, schema_name="forge.experiment-manifest"
            )
        except InvariantViolationError as exc:
            raise ValueError(str(exc)) from exc
        return value


# --- Run manifest (§17) ------------------------------------------------------------


class RunDatasetRef(_StrictModel):
    manifest_uri: str
    manifest_sha256: Sha256Hex


class RunKernelSpec(_StrictModel):
    id: str
    implementation: Literal["python", "cpp"]
    version: str
    package_sha256: Sha256Hex


class RunPartitioning(_StrictModel):
    strategy: str
    target_records: int = Field(gt=0)
    planner_version: int = Field(ge=1)


class RunMerge(_StrictModel):
    strategy: str
    version: int = Field(ge=1)


class RunReproducibility(_StrictModel):
    seed: int
    python: str
    cpp_standard: str
    forge_commit: str


class RunExecution(_StrictModel):
    max_attempts: int = Field(ge=1)
    lease_seconds: int = Field(gt=0)
    worker_concurrency: int = Field(ge=1)
    durability: str


class RunManifest(_StrictModel):
    schema_version: str
    run_id: str
    created_utc: datetime
    dataset: RunDatasetRef
    kernel: RunKernelSpec
    parameters: dict[str, object] = Field(default_factory=dict)
    partitioning: RunPartitioning
    merge: RunMerge
    reproducibility: RunReproducibility
    execution: RunExecution

    @field_validator("schema_version")
    @classmethod
    def _check_schema_version(cls, value: str) -> str:
        match = _RUN_SCHEMA_VERSION_PATTERN.match(value)
        if match is None:
            raise ValueError(
                f"malformed run manifest schema_version {value!r}, expected forge.run.vN"
            )
        major = int(match.group("major"))
        if major not in SUPPORTED_RUN_MANIFEST_MAJOR_VERSIONS:
            raise ValueError(
                f"unsupported forge.run major version {major}; "
                f"supported: {SUPPORTED_RUN_MANIFEST_MAJOR_VERSIONS}"
            )
        return value
