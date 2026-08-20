import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest
from forge.datasets.generator import GeneratorConfig, generate_dataset
from forge.datasets.reader import DatasetFileReader
from forge.domain.manifests import (
    ExperimentDatasetRef,
    ExperimentExecution,
    ExperimentKernelSpec,
    ExperimentManifest,
    ExperimentPartitioning,
    ExperimentResult,
)
from forge.kernels.base import KernelRegistry, RegisteredKernel
from forge.kernels.checksum_chain import KERNEL_ID as CHECKSUM_KERNEL_ID
from forge.kernels.checksum_chain import KERNEL_VERSION as CHECKSUM_KERNEL_VERSION
from forge.kernels.checksum_chain import ChecksumChainKernel
from forge.kernels.event_counts import KERNEL_ID as COUNTS_KERNEL_ID
from forge.kernels.event_counts import KERNEL_VERSION as COUNTS_KERNEL_VERSION
from forge.kernels.event_counts import EventCountsKernel
from forge.kernels.instrument_sums import KERNEL_ID as SUMS_KERNEL_ID
from forge.kernels.instrument_sums import KERNEL_VERSION as SUMS_KERNEL_VERSION
from forge.kernels.instrument_sums import InstrumentSumKernel
from forge.planner.reference_engine import run_reference_experiment

DATASET_ID = "synthetic-orders-v1-seed-17"


def _registry() -> KernelRegistry:
    registry = KernelRegistry()
    registry.register(
        RegisteredKernel(COUNTS_KERNEL_ID, COUNTS_KERNEL_VERSION, "python", EventCountsKernel)
    )
    registry.register(
        RegisteredKernel(SUMS_KERNEL_ID, SUMS_KERNEL_VERSION, "python", InstrumentSumKernel)
    )
    registry.register(
        RegisteredKernel(CHECKSUM_KERNEL_ID, CHECKSUM_KERNEL_VERSION, "python", ChecksumChainKernel)
    )
    return registry


def _experiment(dataset_manifest, kernel_id: str, kernel_version: str, *, target: int = 250):
    return ExperimentManifest(
        schema_name="forge.experiment-manifest",
        schema_version=1,
        experiment_id="test-experiment",
        dataset=ExperimentDatasetRef(
            dataset_id=dataset_manifest.dataset_id,
            content_sha256=dataset_manifest.content_sha256,
        ),
        partitioning=ExperimentPartitioning(
            policy="contiguous-record-ranges", policy_version=1, target_records_per_task=target
        ),
        kernel=ExperimentKernelSpec(
            kernel_id=kernel_id,
            kernel_version=kernel_version,
            engine="python",
            parameter_schema_version=1,
            parameters={},
        ),
        execution=ExperimentExecution(
            max_attempts_per_task=3,
            attempt_timeout_seconds=60,
            lease_seconds=30,
            heartbeat_seconds=5,
            max_parallel_tasks=4,
        ),
        result=ExperimentResult(
            schema_id="forge.result", schema_version=1, canonical_merge="ordinal"
        ),
    )


@pytest.fixture
def dataset(tmp_path: Path):
    return generate_dataset(
        tmp_path / "dataset", GeneratorConfig(seed=17, record_count=1_000), dataset_id=DATASET_ID
    )


def _dataset_file(tmp_path: Path) -> Path:
    return tmp_path / "dataset" / "data" / "events-00000.forge"


# --- replay / deterministic output ----------------------------------------------


def test_running_the_same_experiment_twice_produces_the_same_digest(
    tmp_path: Path, dataset
) -> None:
    experiment = _experiment(dataset, "forge.event-counts", "1.0.0")

    first = run_reference_experiment(
        _dataset_file(tmp_path),
        dataset,
        experiment,
        _registry(),
        run_seed=42,
        output_dir=tmp_path / "run1",
    )
    second = run_reference_experiment(
        _dataset_file(tmp_path),
        dataset,
        experiment,
        _registry(),
        run_seed=42,
        output_dir=tmp_path / "run2",
    )

    assert first.canonical_result_digest == second.canonical_result_digest
    assert first.created_utc != second.created_utc  # nondeterministic metadata differs...
    # ...but does not affect the digest, and the raw result bytes are identical too.
    result_a = (tmp_path / "run1" / "result.bin").read_bytes()
    result_b = (tmp_path / "run2" / "result.bin").read_bytes()
    assert result_a == result_b


def test_publishes_a_result_manifest_and_partition_files(tmp_path: Path, dataset) -> None:
    experiment = _experiment(dataset, "forge.event-counts", "1.0.0", target=250)
    manifest = run_reference_experiment(
        _dataset_file(tmp_path),
        dataset,
        experiment,
        _registry(),
        run_seed=1,
        output_dir=tmp_path / "run",
    )

    assert manifest.partition_count == 4
    assert (tmp_path / "run" / "result-manifest.json").exists()
    partition_files = sorted((tmp_path / "run" / "partitions").glob("*.result"))
    assert len(partition_files) == 4

    on_disk = json.loads((tmp_path / "run" / "result-manifest.json").read_text())
    assert on_disk["canonical_result_digest"] == manifest.canonical_result_digest


# --- invalid parameter ----------------------------------------------------------


def test_invalid_kernel_parameter_fails_before_any_partition_executes(
    tmp_path: Path, dataset
) -> None:
    experiment = _experiment(dataset, "forge.event-counts", "1.0.0")
    experiment = experiment.model_copy(
        update={"kernel": experiment.kernel.model_copy(update={"parameters": {"unexpected": 1}})}
    )

    with pytest.raises(ValueError, match="unexpected"):
        run_reference_experiment(
            _dataset_file(tmp_path),
            dataset,
            experiment,
            _registry(),
            run_seed=1,
            output_dir=tmp_path / "run",
        )
    assert not (tmp_path / "run").exists()


# --- differential: partitioned engine vs. brute-force oracle -----------------------


def test_event_counts_matches_a_brute_force_oracle(tmp_path: Path, dataset) -> None:
    experiment = _experiment(dataset, "forge.event-counts", "1.0.0", target=137)
    manifest = run_reference_experiment(
        _dataset_file(tmp_path),
        dataset,
        experiment,
        _registry(),
        run_seed=1,
        output_dir=tmp_path / "run",
    )
    engine_result = json.loads((tmp_path / "run" / "result.bin").read_bytes())

    # Brute force: ignore partitioning entirely, count directly over every record.
    reader = DatasetFileReader.open(_dataset_file(tmp_path))
    oracle_counts: Counter[int] = Counter()
    for record in reader.iter_records():
        oracle_counts[record.event_type] += 1

    assert engine_result["total"] == sum(oracle_counts.values())
    assert engine_result["by_event_type"] == {str(k): v for k, v in oracle_counts.items()}
    assert manifest.partition_count > 1  # actually exercised partitioning, not a single chunk


def test_instrument_sum_matches_a_brute_force_oracle(tmp_path: Path, dataset) -> None:
    experiment = _experiment(dataset, "forge.instrument-sum", "1.0.0", target=91)
    run_reference_experiment(
        _dataset_file(tmp_path),
        dataset,
        experiment,
        _registry(),
        run_seed=1,
        output_dir=tmp_path / "run",
    )
    engine_result = json.loads((tmp_path / "run" / "result.bin").read_bytes())

    reader = DatasetFileReader.open(_dataset_file(tmp_path))
    oracle_sums: dict[int, int] = defaultdict(int)
    for record in reader.iter_records():
        oracle_sums[record.instrument_id] += record.value_i64

    assert engine_result["sums"] == {str(k): v for k, v in oracle_sums.items()}


def _run_result(
    tmp_path: Path, dataset, kernel_id: str, kernel_version: str, target: int, out: str
):
    experiment = _experiment(dataset, kernel_id, kernel_version, target=target)
    run_reference_experiment(
        _dataset_file(tmp_path),
        dataset,
        experiment,
        _registry(),
        run_seed=1,
        output_dir=tmp_path / out,
    )
    return json.loads((tmp_path / out / "result.bin").read_bytes())


# --- partition-shape sensitivity: the property the merge-order test is really about ---


def test_associative_kernel_digest_is_invariant_to_partition_boundaries(
    tmp_path: Path, dataset
) -> None:
    """event-counts is associative and commutative — splitting the same dataset into
    4 tasks vs. 2 tasks must still merge to the same final result (§24)."""
    fine = _run_result(tmp_path, dataset, "forge.event-counts", "1.0.0", target=250, out="fine")
    coarse = _run_result(tmp_path, dataset, "forge.event-counts", "1.0.0", target=500, out="coarse")
    assert fine == coarse


def test_checksum_chain_digest_changes_with_partition_boundaries(tmp_path: Path, dataset) -> None:
    """checksum-chain is deliberately order/boundary-sensitive (see
    `forge/kernels/checksum_chain.py`) — a different task granularity chains a
    different sequence of partition digests, so the final digest must differ. This
    is the sharpest end-to-end evidence that the engine's merge step is actually
    partition-structure-sensitive rather than silently normalizing everything to the
    same answer regardless of how the work was split."""
    fine = _run_result(tmp_path, dataset, "forge.checksum-chain", "1.0.0", target=173, out="fine")
    coarse = _run_result(
        tmp_path, dataset, "forge.checksum-chain", "1.0.0", target=500, out="coarse"
    )
    assert fine["sha256"] != coarse["sha256"]
