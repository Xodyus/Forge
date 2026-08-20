"""Strict validating dataset reader (§273 Week 3, §362 validation checklist).

Checks header magic/version/lengths at `open()` before anything is trusted, then
verifies the payload checksum and iterates records — each is a separate, explicit
step so a caller can choose how much validation a read needs (e.g. skip the full
checksum scan for a quick record count) without silently skipping the length checks
that make it safe to read at all.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

from forge.datasets.format import (
    DATASET_HEADER_BYTES,
    EVENT_RECORD_BYTES,
    DatasetFileHeader,
    EventRecord,
)

_READ_CHUNK_BYTES = 1024 * 1024


class DatasetIntegrityError(ValueError):
    """Raised when a dataset file fails header, length, or checksum validation."""


class DatasetFileReader:
    def __init__(self, path: Path, header: DatasetFileHeader) -> None:
        self.path = path
        self.header = header

    @classmethod
    def open(cls, path: Path) -> DatasetFileReader:
        file_size = path.stat().st_size
        if file_size < DATASET_HEADER_BYTES:
            raise DatasetIntegrityError(
                f"{path}: file too small to contain a header "
                f"({file_size} < {DATASET_HEADER_BYTES} bytes)"
            )

        with path.open("rb") as handle:
            header_bytes = handle.read(DATASET_HEADER_BYTES)
        try:
            header = DatasetFileHeader.unpack(header_bytes)
        except ValueError as exc:
            raise DatasetIntegrityError(f"{path}: invalid header: {exc}") from exc

        # Checked arithmetic (§362): Python ints don't overflow, but the header's
        # claimed size must still match the file actually on disk.
        expected_size = DATASET_HEADER_BYTES + header.record_count * header.record_bytes
        if file_size != expected_size:
            raise DatasetIntegrityError(
                f"{path}: expected {expected_size} bytes for {header.record_count} records "
                f"({header.record_bytes} bytes each) plus header, got {file_size}"
            )

        return cls(path, header)

    def verify_payload_digest(self) -> None:
        """Full-validation mode (§362): hash every payload byte and compare against
        the header's declared `payload_sha256`. Sampled validation is not
        implemented — §362 only requires that a reader record which mode it used,
        and "full" is the only mode this reader offers."""
        hasher = hashlib.sha256()
        with self.path.open("rb") as handle:
            handle.seek(DATASET_HEADER_BYTES)
            for chunk in iter(lambda: handle.read(_READ_CHUNK_BYTES), b""):
                hasher.update(chunk)
        actual = hasher.digest()
        if actual != self.header.payload_sha256:
            raise DatasetIntegrityError(
                f"{self.path}: payload checksum mismatch "
                f"(declared {self.header.payload_sha256.hex()}, computed {actual.hex()})"
            )

    def iter_records(self) -> Iterator[EventRecord]:
        yield from self.read_records(record_start=0, record_count=self.header.record_count)

    def read_records(self, *, record_start: int, record_count: int) -> Iterator[EventRecord]:
        """Read a contiguous slice — e.g. one partition's records, by
        `PartitionDescriptor.record_start`/`record_count` — without loading the
        whole file. Takes plain ints rather than a `PartitionDescriptor` so this
        module doesn't have to depend on `forge.domain` for a read path.

        Validates the range eagerly (not lazily on first iteration) so a caller who
        never consumes the returned iterator still finds out immediately that the
        range was invalid, matching `open()`'s fail-fast behavior.
        """
        if record_start < 0 or record_count < 0:
            raise ValueError("record_start and record_count must be non-negative")
        if record_start + record_count > self.header.record_count:
            raise DatasetIntegrityError(
                f"{self.path}: requested records [{record_start}, {record_start + record_count}) "
                f"exceed file record_count {self.header.record_count}"
            )
        return self._read_records(record_start, record_count)

    def _read_records(self, record_start: int, record_count: int) -> Iterator[EventRecord]:
        with self.path.open("rb") as handle:
            handle.seek(DATASET_HEADER_BYTES + record_start * EVENT_RECORD_BYTES)
            for index in range(record_start, record_start + record_count):
                chunk = handle.read(EVENT_RECORD_BYTES)
                if len(chunk) != EVENT_RECORD_BYTES:
                    raise DatasetIntegrityError(
                        f"{self.path}: truncated record {index} of {self.header.record_count}"
                    )
                try:
                    yield EventRecord.unpack(chunk)
                except ValueError as exc:
                    raise DatasetIntegrityError(
                        f"{self.path}: invalid record {index}: {exc}"
                    ) from exc
