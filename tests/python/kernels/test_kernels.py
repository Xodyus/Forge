import json

import pytest
from forge.datasets.format import EventRecord
from forge.kernels.base import KernelParameterError
from forge.kernels.checksum_chain import ChecksumChainKernel
from forge.kernels.event_counts import EventCountsKernel
from forge.kernels.instrument_sums import InstrumentSumKernel


def _record(**overrides: object) -> EventRecord:
    fields: dict[str, object] = dict(
        timestamp_ns=1,
        instrument_id=1,
        event_type=1,
        flags=0,
        value_i64=0,
        quantity=0,
        sequence=0,
    )
    fields.update(overrides)
    return EventRecord(**fields)  # type: ignore[arg-type]


ALL_KERNELS = [EventCountsKernel(), InstrumentSumKernel(), ChecksumChainKernel()]


@pytest.mark.parametrize("kernel", ALL_KERNELS)
def test_validate_parameters_accepts_empty_dict(kernel: object) -> None:
    kernel.validate_parameters({})  # type: ignore[attr-defined]


@pytest.mark.parametrize("kernel", ALL_KERNELS)
def test_validate_parameters_rejects_unknown_key(kernel: object) -> None:
    with pytest.raises(KernelParameterError):
        kernel.validate_parameters({"unexpected": 1})  # type: ignore[attr-defined]


@pytest.mark.parametrize("kernel", ALL_KERNELS)
def test_execute_partition_is_deterministic(kernel: object) -> None:
    records = [_record(sequence=i, instrument_id=i % 3, value_i64=i) for i in range(20)]
    first = kernel.execute_partition(records, {})  # type: ignore[attr-defined]
    second = kernel.execute_partition(records, {})  # type: ignore[attr-defined]
    assert first == second


@pytest.mark.parametrize("kernel", ALL_KERNELS)
def test_empty_partition_produces_valid_json_result(kernel: object) -> None:
    result = kernel.execute_partition([], {})  # type: ignore[attr-defined]
    json.loads(result)  # must not raise


# --- event counts -----------------------------------------------------------------


def test_event_counts_execute_partition() -> None:
    records = [_record(event_type=1), _record(event_type=1), _record(event_type=2)]
    result = json.loads(EventCountsKernel().execute_partition(records, {}))
    assert result == {"total": 3, "by_event_type": {"1": 2, "2": 1}}


def test_event_counts_merge_sums_across_partitions() -> None:
    kernel = EventCountsKernel()
    a = kernel.execute_partition([_record(event_type=1), _record(event_type=2)], {})
    b = kernel.execute_partition([_record(event_type=1)], {})
    merged = json.loads(kernel.merge([a, b], {}))
    assert merged == {"total": 3, "by_event_type": {"1": 2, "2": 1}}


# --- instrument sums ----------------------------------------------------------


def test_instrument_sum_execute_partition() -> None:
    records = [
        _record(instrument_id=1, value_i64=10),
        _record(instrument_id=1, value_i64=5),
        _record(instrument_id=2, value_i64=-3),
    ]
    result = json.loads(InstrumentSumKernel().execute_partition(records, {}))
    assert result == {"sums": {"1": 15, "2": -3}}


def test_instrument_sum_merge_sums_across_partitions() -> None:
    kernel = InstrumentSumKernel()
    a = kernel.execute_partition([_record(instrument_id=1, value_i64=10)], {})
    b = kernel.execute_partition([_record(instrument_id=1, value_i64=5)], {})
    merged = json.loads(kernel.merge([a, b], {}))
    assert merged == {"sums": {"1": 15}}


# --- checksum chain: order sensitivity -----------------------------------------


def test_checksum_chain_merge_is_order_sensitive() -> None:
    kernel = ChecksumChainKernel()
    a = kernel.execute_partition([_record(sequence=0)], {})
    b = kernel.execute_partition([_record(sequence=1)], {})

    forward = kernel.merge([a, b], {})
    backward = kernel.merge([b, a], {})
    assert forward != backward


def test_checksum_chain_execute_partition_is_order_sensitive() -> None:
    kernel = ChecksumChainKernel()
    forward = kernel.execute_partition([_record(sequence=0), _record(sequence=1)], {})
    backward = kernel.execute_partition([_record(sequence=1), _record(sequence=0)], {})
    assert forward != backward


def test_checksum_chain_matches_manual_sha256() -> None:
    import hashlib

    records = [_record(sequence=i) for i in range(5)]
    kernel = ChecksumChainKernel()
    result = json.loads(kernel.execute_partition(records, {}))

    expected = hashlib.sha256()
    for record in records:
        expected.update(record.pack())
    assert result["sha256"] == expected.hexdigest()
