"""Dataset manifest schema (Appendix C §359).

``content_sha256`` is defined by §359 as "digest of canonical file descriptors" —
unlike the experiment/run manifests, a dataset manifest can be *internally* checked
for consistency without touching real file bytes: recompute the canonical digest of
its own ``files`` list and compare. That check runs in ``_check_content_digest``
below and is what the "checksum mismatch" invalid fixture exercises.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from forge.domain.canonical import canonical_json_bytes, content_digest
from forge.domain.invariants import InvariantViolationError, assert_schema_version_supported

Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

SUPPORTED_DATASET_MANIFEST_SCHEMA_VERSIONS = (1,)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class DatasetGeneratorInfo(_StrictModel):
    generator_id: str
    generator_version: str
    seed: int


class DatasetRecordSchema(_StrictModel):
    id: str
    version: int = Field(ge=1)
    record_bytes: int = Field(gt=0)
    byte_order: str


class DatasetFileEntry(_StrictModel):
    relative_path: str
    byte_count: int = Field(ge=0)
    record_count: int = Field(ge=0)
    sha256: Sha256Hex
    payload_sha256: Sha256Hex

    @field_validator("relative_path")
    @classmethod
    def _check_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute():
            raise ValueError(f"relative_path must be relative, got {value!r}")
        if ".." in path.parts:
            raise ValueError(f"relative_path must not contain '..', got {value!r}")
        return value


class DatasetManifest(_StrictModel):
    schema_name: str = Field(alias="schema")
    schema_version: int
    dataset_id: str
    created_by: DatasetGeneratorInfo
    record_schema: DatasetRecordSchema
    files: list[DatasetFileEntry]
    generation: dict[str, object]
    content_sha256: Sha256Hex

    @field_validator("schema_name")
    @classmethod
    def _check_schema_name(cls, value: str) -> str:
        if value != "forge.dataset-manifest":
            raise ValueError(f"unsupported schema {value!r}, expected forge.dataset-manifest")
        return value

    @field_validator("schema_version")
    @classmethod
    def _check_schema_version(cls, value: int) -> int:
        try:
            assert_schema_version_supported(
                value,
                SUPPORTED_DATASET_MANIFEST_SCHEMA_VERSIONS,
                schema_name="forge.dataset-manifest",
            )
        except InvariantViolationError as exc:
            raise ValueError(str(exc)) from exc
        return value

    @field_validator("files")
    @classmethod
    def _check_no_duplicate_paths(cls, files: list[DatasetFileEntry]) -> list[DatasetFileEntry]:
        seen: set[str] = set()
        for entry in files:
            if entry.relative_path in seen:
                raise ValueError(f"duplicate file relative_path: {entry.relative_path!r}")
            seen.add(entry.relative_path)
        return files

    @model_validator(mode="after")
    def _check_content_digest(self) -> DatasetManifest:
        expected = str(content_digest(_FilesOnly(files=self.files)))
        actual = f"sha256:{self.content_sha256}"
        if actual != expected:
            raise ValueError(
                f"content_sha256 does not match digest of canonical file descriptors: "
                f"declared {actual}, computed {expected}"
            )
        return self


class _FilesOnly(_StrictModel):
    """Isolates exactly what §359's "digest of canonical file descriptors" covers,
    so the manifest's own content_sha256 field isn't part of its own input."""

    files: list[DatasetFileEntry]


def compute_content_sha256(files: list[DatasetFileEntry]) -> str:
    """The same digest `DatasetManifest._check_content_digest` verifies — exposed so
    a writer (:mod:`forge.datasets.generator`) can compute `content_sha256` before
    constructing the manifest, instead of guessing and letting validation fail."""
    return content_digest(_FilesOnly(files=files)).hex_value


__all__ = [
    "DatasetFileEntry",
    "DatasetGeneratorInfo",
    "DatasetManifest",
    "DatasetRecordSchema",
    "canonical_json_bytes",
    "compute_content_sha256",
]
