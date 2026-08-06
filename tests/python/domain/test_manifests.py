import json
from pathlib import Path

import pytest
from forge.domain.canonical import canonical_json_bytes, content_digest
from forge.domain.manifests import ExperimentManifest, RunManifest
from pydantic import ValidationError

FIXTURES = Path(__file__).parents[2] / "fixtures" / "manifests"


def _load(*parts: str) -> dict:
    return json.loads((FIXTURES.joinpath(*parts)).read_text(encoding="utf-8"))


# --- valid fixtures parse and round-trip -------------------------------------------


def test_valid_experiment_manifest_parses() -> None:
    manifest = ExperimentManifest.model_validate(_load("valid", "experiment-manifest.json"))
    assert manifest.experiment_id == "instrument-stats-example"
    assert manifest.schema_version == 1


def test_valid_run_manifest_parses() -> None:
    manifest = RunManifest.model_validate(_load("valid", "run-manifest.json"))
    assert manifest.schema_version == "forge.run.v1"


def test_canonical_bytes_are_stable_across_reparse() -> None:
    data = _load("valid", "experiment-manifest.json")
    first = ExperimentManifest.model_validate(data)
    second = ExperimentManifest.model_validate(json.loads(json.dumps(data)))
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert content_digest(first) == content_digest(second)


def test_canonical_bytes_are_sorted_and_compact() -> None:
    manifest = ExperimentManifest.model_validate(_load("valid", "experiment-manifest.json"))
    text = canonical_json_bytes(manifest).decode("utf-8")
    assert ", " not in text  # compact separators
    assert ": " not in text


# --- invalid fixtures are rejected --------------------------------------------------


@pytest.mark.parametrize(
    "fixture",
    ["experiment-unknown-field.json", "experiment-bad-version.json"],
)
def test_invalid_experiment_fixtures_are_rejected(fixture: str) -> None:
    with pytest.raises(ValidationError):
        ExperimentManifest.model_validate(_load("invalid", fixture))


@pytest.mark.parametrize(
    "fixture",
    ["run-unknown-field.json", "run-bad-version.json"],
)
def test_invalid_run_fixtures_are_rejected(fixture: str) -> None:
    with pytest.raises(ValidationError):
        RunManifest.model_validate(_load("invalid", fixture))


# --- direct constraint checks (not fixture-driven) ---------------------------------


def test_run_manifest_rejects_malformed_schema_version_string() -> None:
    data = _load("valid", "run-manifest.json")
    data["schema_version"] = "not-a-version"
    with pytest.raises(ValidationError, match="malformed"):
        RunManifest.model_validate(data)


def test_experiment_manifest_rejects_negative_lease_seconds() -> None:
    data = _load("valid", "experiment-manifest.json")
    data["execution"]["lease_seconds"] = -1
    with pytest.raises(ValidationError):
        ExperimentManifest.model_validate(data)


def test_experiment_manifest_rejects_zero_max_parallel_tasks() -> None:
    data = _load("valid", "experiment-manifest.json")
    data["execution"]["max_parallel_tasks"] = 0
    with pytest.raises(ValidationError):
        ExperimentManifest.model_validate(data)


def test_experiment_manifest_rejects_wrong_schema_name() -> None:
    data = _load("valid", "experiment-manifest.json")
    data["schema"] = "forge.something-else"
    with pytest.raises(ValidationError, match="unsupported schema"):
        ExperimentManifest.model_validate(data)


def test_experiment_manifest_rejects_unsupported_engine() -> None:
    data = _load("valid", "experiment-manifest.json")
    data["kernel"]["engine"] = "rust"
    with pytest.raises(ValidationError):
        ExperimentManifest.model_validate(data)
