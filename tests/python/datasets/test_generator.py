import json
from pathlib import Path

import pytest
from forge.datasets.format import DATASET_HEADER_BYTES, EVENT_RECORD_BYTES, DatasetFileHeader
from forge.datasets.generator import GeneratorConfig, generate_dataset
from forge.datasets.manifest import DatasetManifest

DATASET_ID = "synthetic-orders-v1-seed-17"


def test_generating_twice_from_the_same_config_is_byte_identical(tmp_path: Path) -> None:
    config = GeneratorConfig(seed=17, record_count=1_000)
    first = generate_dataset(tmp_path / "a", config, dataset_id=DATASET_ID)
    second = generate_dataset(tmp_path / "b", config, dataset_id=DATASET_ID)

    assert first.content_sha256 == second.content_sha256
    first_bytes = (tmp_path / "a" / "data" / "events-00000.forge").read_bytes()
    second_bytes = (tmp_path / "b" / "data" / "events-00000.forge").read_bytes()
    assert first_bytes == second_bytes


def test_different_seeds_produce_different_content(tmp_path: Path) -> None:
    config_a = GeneratorConfig(seed=1, record_count=200)
    config_b = GeneratorConfig(seed=2, record_count=200)
    a = generate_dataset(tmp_path / "a", config_a, dataset_id=DATASET_ID)
    b = generate_dataset(tmp_path / "b", config_b, dataset_id=DATASET_ID)
    assert a.content_sha256 != b.content_sha256


def test_generated_file_has_a_valid_header(tmp_path: Path) -> None:
    generate_dataset(tmp_path, GeneratorConfig(seed=17, record_count=64), dataset_id=DATASET_ID)
    raw = (tmp_path / "data" / "events-00000.forge").read_bytes()
    header = DatasetFileHeader.unpack(raw[:DATASET_HEADER_BYTES])
    assert header.record_count == 64
    assert len(raw) == DATASET_HEADER_BYTES + 64 * EVENT_RECORD_BYTES


def test_zero_record_dataset_is_valid(tmp_path: Path) -> None:
    config = GeneratorConfig(seed=17, record_count=0)
    manifest = generate_dataset(tmp_path, config, dataset_id=DATASET_ID)
    assert manifest.files[0].record_count == 0
    raw = (tmp_path / "data" / "events-00000.forge").read_bytes()
    assert len(raw) == DATASET_HEADER_BYTES


def test_manifest_json_on_disk_round_trips_through_dataset_manifest(tmp_path: Path) -> None:
    generate_dataset(tmp_path, GeneratorConfig(seed=17, record_count=10), dataset_id=DATASET_ID)
    data = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest = DatasetManifest.model_validate(data)
    assert manifest.dataset_id == DATASET_ID
    assert manifest.files[0].record_count == 10


def test_generator_config_rejects_negative_record_count() -> None:
    with pytest.raises(ValueError, match="record_count"):
        GeneratorConfig(seed=1, record_count=-1)


def test_generator_config_rejects_empty_event_type_weights() -> None:
    with pytest.raises(ValueError, match="event_type_weights"):
        GeneratorConfig(seed=1, record_count=10, event_type_weights={})


def test_generator_config_rejects_zero_sum_weights() -> None:
    with pytest.raises(ValueError, match="event_type_weights"):
        GeneratorConfig(seed=1, record_count=10, event_type_weights={1: 0.0})


def test_generator_config_rejects_backwards_timestamp_step_range() -> None:
    with pytest.raises(ValueError, match="timestamp step"):
        GeneratorConfig(seed=1, record_count=10, timestamp_step_min=100, timestamp_step_max=1)
