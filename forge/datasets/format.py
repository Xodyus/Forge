"""Binary layout for the synthetic event record and dataset file header
(Appendix C §357–§358, Table 132 and Table 133).

This module only defines and (de)serializes the fixed layout — encode/decode a
single record or header from bytes already in memory. It intentionally does not
generate datasets, open files, iterate partitions, or verify payload checksums
against real file bytes: that is the seeded generator and reader, Week 3 (E02-02,
E02-03).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# --- Event record (Table 132): 32 bytes, little-endian ----------------------------

EVENT_RECORD_BYTES = 32

# offset  size  field           struct code
#      0     8  timestamp_ns    Q
#      8     4  instrument_id   I
#     12     1  event_type      B
#     13     1  flags           B
#     14     2  reserved        H  (must be zero in schema v1)
#     16     8  value_i64       q
#     24     4  quantity        I
#     28     4  sequence        I
_EVENT_RECORD_STRUCT = struct.Struct("<QIBBHqII")

assert _EVENT_RECORD_STRUCT.size == EVENT_RECORD_BYTES


@dataclass(frozen=True, slots=True)
class EventRecord:
    timestamp_ns: int
    instrument_id: int
    event_type: int
    flags: int
    value_i64: int
    quantity: int
    sequence: int
    reserved: int = 0

    def __post_init__(self) -> None:
        if self.reserved != 0:
            raise ValueError("reserved field must be zero in schema v1")
        _check_unsigned(self.timestamp_ns, bits=64, name="timestamp_ns")
        _check_unsigned(self.instrument_id, bits=32, name="instrument_id")
        _check_unsigned(self.event_type, bits=8, name="event_type")
        _check_unsigned(self.flags, bits=8, name="flags")
        _check_signed(self.value_i64, bits=64, name="value_i64")
        _check_unsigned(self.quantity, bits=32, name="quantity")
        _check_unsigned(self.sequence, bits=32, name="sequence")

    def pack(self) -> bytes:
        return _EVENT_RECORD_STRUCT.pack(
            self.timestamp_ns,
            self.instrument_id,
            self.event_type,
            self.flags,
            self.reserved,
            self.value_i64,
            self.quantity,
            self.sequence,
        )

    @classmethod
    def unpack(cls, data: bytes) -> EventRecord:
        if len(data) != EVENT_RECORD_BYTES:
            raise ValueError(f"expected {EVENT_RECORD_BYTES} bytes, got {len(data)}")
        (
            timestamp_ns,
            instrument_id,
            event_type,
            flags,
            reserved,
            value_i64,
            quantity,
            sequence,
        ) = _EVENT_RECORD_STRUCT.unpack(data)
        return cls(
            timestamp_ns=timestamp_ns,
            instrument_id=instrument_id,
            event_type=event_type,
            flags=flags,
            reserved=reserved,
            value_i64=value_i64,
            quantity=quantity,
            sequence=sequence,
        )


def _check_unsigned(value: int, *, bits: int, name: str) -> None:
    if not (0 <= value < (1 << bits)):
        raise ValueError(f"{name} must fit in an unsigned {bits}-bit field, got {value}")


def _check_signed(value: int, *, bits: int, name: str) -> None:
    limit = 1 << (bits - 1)
    if not (-limit <= value < limit):
        raise ValueError(f"{name} must fit in a signed {bits}-bit field, got {value}")


# --- Dataset file header (Table 133): 128 bytes, little-endian --------------------

DATASET_HEADER_BYTES = 128
DATASET_MAGIC = b"FORGEV1\0"
assert len(DATASET_MAGIC) == 8

# offset  size  field             struct code
#      0     8  magic             8s
#      8     2  header_version    H
#     10     2  record_schema     H
#     12     4  header_bytes      I
#     16     8  record_count      Q
#     24     4  record_bytes      I  (must equal 32 for schema v1)
#     28     4  flags             I
#     32    32  payload_sha256    32s
#     64    32  manifest_sha256   32s
#     96    32  reserved          32s (zero until assigned)
_HEADER_STRUCT = struct.Struct("<8sHHIQII32s32s32s")

assert _HEADER_STRUCT.size == DATASET_HEADER_BYTES


@dataclass(frozen=True, slots=True)
class DatasetFileHeader:
    header_version: int
    record_schema: int
    header_bytes: int
    record_count: int
    record_bytes: int
    flags: int
    payload_sha256: bytes
    manifest_sha256: bytes
    magic: bytes = DATASET_MAGIC
    reserved: bytes = b"\x00" * 32

    def __post_init__(self) -> None:
        if self.magic != DATASET_MAGIC:
            raise ValueError(f"bad magic: {self.magic!r}")
        if self.record_bytes != EVENT_RECORD_BYTES:
            raise ValueError(
                f"record_bytes must equal {EVENT_RECORD_BYTES} for schema v1, "
                f"got {self.record_bytes}"
            )
        if self.header_bytes != DATASET_HEADER_BYTES:
            raise ValueError(
                f"header_bytes must equal {DATASET_HEADER_BYTES} for schema v1, "
                f"got {self.header_bytes}"
            )
        _check_unsigned(self.header_version, bits=16, name="header_version")
        _check_unsigned(self.record_schema, bits=16, name="record_schema")
        _check_unsigned(self.record_count, bits=64, name="record_count")
        if len(self.payload_sha256) != 32:
            raise ValueError("payload_sha256 must be 32 raw bytes")
        if len(self.manifest_sha256) != 32:
            raise ValueError("manifest_sha256 must be 32 raw bytes")
        if len(self.reserved) != 32:
            raise ValueError("reserved must be 32 bytes")
        if self.reserved != b"\x00" * 32:
            raise ValueError("reserved must be zero until assigned by a compatible version")

    def pack(self) -> bytes:
        return _HEADER_STRUCT.pack(
            self.magic,
            self.header_version,
            self.record_schema,
            self.header_bytes,
            self.record_count,
            self.record_bytes,
            self.flags,
            self.payload_sha256,
            self.manifest_sha256,
            self.reserved,
        )

    @classmethod
    def unpack(cls, data: bytes) -> DatasetFileHeader:
        if len(data) != DATASET_HEADER_BYTES:
            raise ValueError(f"expected {DATASET_HEADER_BYTES} bytes, got {len(data)}")
        (
            magic,
            header_version,
            record_schema,
            header_bytes,
            record_count,
            record_bytes,
            flags,
            payload_sha256,
            manifest_sha256,
            reserved,
        ) = _HEADER_STRUCT.unpack(data)
        return cls(
            magic=magic,
            header_version=header_version,
            record_schema=record_schema,
            header_bytes=header_bytes,
            record_count=record_count,
            record_bytes=record_bytes,
            flags=flags,
            payload_sha256=payload_sha256,
            manifest_sha256=manifest_sha256,
            reserved=reserved,
        )
