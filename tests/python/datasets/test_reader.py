from pathlib import Path

import pytest
from forge.datasets.format import DATASET_HEADER_BYTES, DATASET_MAGIC
from forge.datasets.generator import GeneratorConfig, generate_dataset
from forge.datasets.reader import DatasetFileReader, DatasetIntegrityError

DATASET_ID = "synthetic-orders-v1-seed-17"


def _generate(tmp_path: Path, record_count: int) -> Path:
    config = GeneratorConfig(seed=17, record_count=record_count)
    generate_dataset(tmp_path, config, dataset_id=DATASET_ID)
    return tmp_path / "data" / "events-00000.forge"


# --- round trip ----------------------------------------------------------------


def test_round_trip_reads_every_record(tmp_path: Path) -> None:
    path = _generate(tmp_path, 250)
    reader = DatasetFileReader.open(path)
    assert reader.header.record_count == 250
    reader.verify_payload_digest()
    records = list(reader.iter_records())
    assert len(records) == 250
    assert [r.sequence for r in records] == list(range(250))


def test_timestamps_are_nondecreasing(tmp_path: Path) -> None:
    path = _generate(tmp_path, 100)
    reader = DatasetFileReader.open(path)
    timestamps = [r.timestamp_ns for r in reader.iter_records()]
    assert timestamps == sorted(timestamps)


# --- boundary: zero records ------------------------------------------------------


def test_zero_record_file_opens_and_iterates_empty(tmp_path: Path) -> None:
    path = _generate(tmp_path, 0)
    reader = DatasetFileReader.open(path)
    assert reader.header.record_count == 0
    reader.verify_payload_digest()
    assert list(reader.iter_records()) == []


# --- truncation --------------------------------------------------------------


def test_truncated_file_below_header_size_is_rejected(tmp_path: Path) -> None:
    path = _generate(tmp_path, 10)
    path.write_bytes(path.read_bytes()[: DATASET_HEADER_BYTES - 1])
    with pytest.raises(DatasetIntegrityError, match="too small"):
        DatasetFileReader.open(path)


def test_truncated_payload_is_rejected_at_open(tmp_path: Path) -> None:
    path = _generate(tmp_path, 10)
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(DatasetIntegrityError, match="expected"):
        DatasetFileReader.open(path)


# --- corruption --------------------------------------------------------------


def test_corrupted_magic_is_rejected_at_open(tmp_path: Path) -> None:
    path = _generate(tmp_path, 10)
    raw = bytearray(path.read_bytes())
    raw[0:8] = b"BADMAGIC"
    path.write_bytes(raw)
    with pytest.raises(DatasetIntegrityError, match="invalid header"):
        DatasetFileReader.open(path)


def test_corrupted_payload_byte_passes_open_but_fails_digest_check(tmp_path: Path) -> None:
    path = _generate(tmp_path, 10)
    raw = bytearray(path.read_bytes())
    raw[DATASET_HEADER_BYTES] ^= 0xFF  # flip one byte inside the payload, not the header
    path.write_bytes(raw)

    reader = DatasetFileReader.open(path)  # length still matches; only content changed
    with pytest.raises(DatasetIntegrityError, match="checksum mismatch"):
        reader.verify_payload_digest()


def test_default_generated_magic_matches_constant(tmp_path: Path) -> None:
    path = _generate(tmp_path, 1)
    reader = DatasetFileReader.open(path)
    assert reader.header.magic == DATASET_MAGIC
