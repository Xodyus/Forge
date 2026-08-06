import pytest
from forge.datasets.format import (
    DATASET_HEADER_BYTES,
    DATASET_MAGIC,
    EVENT_RECORD_BYTES,
    DatasetFileHeader,
    EventRecord,
)

# --- EventRecord --------------------------------------------------------------------


def _record(**overrides: object) -> EventRecord:
    fields: dict[str, object] = dict(
        timestamp_ns=1_700_000_000_000,
        instrument_id=7,
        event_type=1,
        flags=0,
        value_i64=-12_345,
        quantity=100,
        sequence=42,
    )
    fields.update(overrides)
    return EventRecord(**fields)  # type: ignore[arg-type]


def test_event_record_round_trips_through_pack_and_unpack() -> None:
    record = _record()
    packed = record.pack()
    assert len(packed) == EVENT_RECORD_BYTES
    assert EventRecord.unpack(packed) == record


def test_event_record_rejects_nonzero_reserved() -> None:
    with pytest.raises(ValueError, match="reserved"):
        _record(reserved=1)


@pytest.mark.parametrize(
    "overrides",
    [
        {"timestamp_ns": -1},
        {"timestamp_ns": 1 << 64},
        {"instrument_id": -1},
        {"instrument_id": 1 << 32},
        {"event_type": -1},
        {"event_type": 256},
        {"flags": 256},
        {"value_i64": -(1 << 63) - 1},
        {"value_i64": 1 << 63},
        {"quantity": -1},
        {"sequence": 1 << 32},
    ],
)
def test_event_record_rejects_out_of_range_fields(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _record(**overrides)


def test_event_record_unpack_rejects_truncated_bytes() -> None:
    with pytest.raises(ValueError, match="expected 32 bytes"):
        EventRecord.unpack(_record().pack()[:-1])


def test_event_record_unpack_rejects_oversized_bytes() -> None:
    with pytest.raises(ValueError, match="expected 32 bytes"):
        EventRecord.unpack(_record().pack() + b"\x00")


def test_event_record_boundary_values_round_trip() -> None:
    boundary = _record(
        timestamp_ns=(1 << 64) - 1,
        instrument_id=(1 << 32) - 1,
        event_type=255,
        flags=255,
        value_i64=(1 << 63) - 1,
        quantity=(1 << 32) - 1,
        sequence=(1 << 32) - 1,
    )
    assert EventRecord.unpack(boundary.pack()) == boundary

    negative_boundary = _record(value_i64=-(1 << 63))
    assert EventRecord.unpack(negative_boundary.pack()) == negative_boundary


# --- DatasetFileHeader ----------------------------------------------------------


def _header(**overrides: object) -> DatasetFileHeader:
    fields: dict[str, object] = dict(
        header_version=1,
        record_schema=1,
        header_bytes=DATASET_HEADER_BYTES,
        record_count=1_000,
        record_bytes=EVENT_RECORD_BYTES,
        flags=0,
        payload_sha256=b"\x01" * 32,
        manifest_sha256=b"\x02" * 32,
    )
    fields.update(overrides)
    return DatasetFileHeader(**fields)  # type: ignore[arg-type]


def test_dataset_file_header_round_trips_through_pack_and_unpack() -> None:
    header = _header()
    packed = header.pack()
    assert len(packed) == DATASET_HEADER_BYTES
    assert DatasetFileHeader.unpack(packed) == header


def test_dataset_file_header_rejects_bad_magic() -> None:
    with pytest.raises(ValueError, match="bad magic"):
        _header(magic=b"BADMAGIC")


def test_dataset_file_header_rejects_wrong_record_bytes() -> None:
    with pytest.raises(ValueError, match="record_bytes"):
        _header(record_bytes=16)


def test_dataset_file_header_rejects_wrong_header_bytes() -> None:
    with pytest.raises(ValueError, match="header_bytes"):
        _header(header_bytes=64)


def test_dataset_file_header_rejects_nonzero_reserved() -> None:
    with pytest.raises(ValueError, match="reserved"):
        _header(reserved=b"\x01" * 32)


def test_dataset_file_header_unpack_rejects_truncated_bytes() -> None:
    with pytest.raises(ValueError, match="expected 128 bytes"):
        DatasetFileHeader.unpack(_header().pack()[:-1])


def test_dataset_file_header_default_magic_matches_constant() -> None:
    assert _header().magic == DATASET_MAGIC
