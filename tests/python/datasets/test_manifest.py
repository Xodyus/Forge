import json
from pathlib import Path

import pytest
from forge.datasets.manifest import DatasetManifest
from pydantic import ValidationError

FIXTURES = Path(__file__).parents[2] / "fixtures" / "manifests"


def _load(*parts: str) -> dict:
    return json.loads((FIXTURES.joinpath(*parts)).read_text(encoding="utf-8"))


def test_valid_dataset_manifest_parses() -> None:
    manifest = DatasetManifest.model_validate(_load("valid", "dataset-manifest.json"))
    assert manifest.dataset_id == "synthetic-orders-v1-seed-17"
    assert len(manifest.files) == 1


# --- the five invalid-fixture categories the roadmap asks for ---------------------


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="unexpected_field|Extra inputs"):
        DatasetManifest.model_validate(_load("invalid", "dataset-unknown-field.json"))


def test_rejects_bad_schema_version() -> None:
    with pytest.raises(ValidationError, match="INV-020|schema_version"):
        DatasetManifest.model_validate(_load("invalid", "dataset-bad-version.json"))


def test_rejects_duplicate_file_identifier() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        DatasetManifest.model_validate(_load("invalid", "dataset-duplicate-file.json"))


def test_rejects_path_traversal() -> None:
    with pytest.raises(ValidationError, match="relative"):
        DatasetManifest.model_validate(_load("invalid", "dataset-path-traversal.json"))


def test_rejects_checksum_mismatch() -> None:
    with pytest.raises(ValidationError, match="content_sha256 does not match"):
        DatasetManifest.model_validate(_load("invalid", "dataset-checksum-mismatch.json"))
