import pytest
from forge.datasets.partitioning import plan_dataset_partitions
from forge.domain.identifiers import DatasetId

DATASET_ID = DatasetId("ds-1")
FILE_ID = "events-00000.forge"
RECORD_BYTES = 32


def _plan(record_count: int, target: int) -> list:
    return plan_dataset_partitions(
        dataset_id=DATASET_ID,
        file_id=FILE_ID,
        record_count=record_count,
        target_records_per_partition=target,
        record_bytes=RECORD_BYTES,
    )


# --- INV-018: complete, non-overlapping coverage -----------------------------------


def test_partitions_cover_every_record_exactly_once_when_evenly_divisible() -> None:
    partitions = _plan(1_000, 250)
    assert len(partitions) == 4
    covered = []
    for partition in partitions:
        end = partition.record_start + partition.record_count
        covered.extend(range(partition.record_start, end))
    assert covered == list(range(1_000))


def test_last_partition_is_short_when_not_evenly_divisible() -> None:
    partitions = _plan(1_005, 250)
    assert [p.record_count for p in partitions] == [250, 250, 250, 250, 5]
    assert sum(p.record_count for p in partitions) == 1_005


def test_partitions_are_contiguous_with_no_gaps_or_overlaps() -> None:
    partitions = _plan(777, 100)
    next_expected_start = 0
    for partition in partitions:
        assert partition.record_start == next_expected_start
        next_expected_start += partition.record_count
    assert next_expected_start == 777


# --- ordinals, ids, and byte ranges ------------------------------------------------


def test_ordinals_and_partition_ids_are_dense_and_sequential() -> None:
    partitions = _plan(500, 100)
    assert [p.ordinal for p in partitions] == [0, 1, 2, 3, 4]
    assert [p.partition_id for p in partitions] == [f"p-{i:06d}" for i in range(5)]


def test_byte_ranges_match_record_bytes() -> None:
    partitions = _plan(500, 200)
    assert partitions[0].byte_start == 0
    assert partitions[0].byte_length == 200 * RECORD_BYTES
    assert partitions[1].byte_start == 200 * RECORD_BYTES
    assert partitions[2].byte_length == 100 * RECORD_BYTES  # 500 - 400 remaining


def test_partition_seed_is_not_populated_at_the_dataset_layer() -> None:
    partitions = _plan(10, 5)
    assert all(p.partition_seed is None for p in partitions)


# --- boundaries and invalid input --------------------------------------------------


def test_zero_records_produces_no_partitions() -> None:
    assert _plan(0, 100) == []


def test_single_partition_when_target_exceeds_record_count() -> None:
    partitions = _plan(10, 1_000)
    assert len(partitions) == 1
    assert partitions[0].record_count == 10


def test_rejects_non_positive_target() -> None:
    with pytest.raises(ValueError, match="target_records_per_partition"):
        _plan(100, 0)


def test_rejects_negative_record_count() -> None:
    with pytest.raises(ValueError, match="record_count"):
        _plan(-1, 100)


# --- determinism ---------------------------------------------------------------


def test_planning_is_deterministic_across_calls() -> None:
    assert _plan(1_234, 137) == _plan(1_234, 137)
