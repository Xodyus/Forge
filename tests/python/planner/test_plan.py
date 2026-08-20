from pathlib import Path

import pytest
from forge.datasets.generator import GeneratorConfig, generate_dataset
from forge.domain.manifests import (
    ExperimentDatasetRef,
    ExperimentExecution,
    ExperimentKernelSpec,
    ExperimentManifest,
    ExperimentPartitioning,
    ExperimentResult,
)
from forge.planner.plan import PlanningError, derive_partition_seed, plan_run_partitions

DATASET_ID = "synthetic-orders-v1-seed-17"


def _generate(tmp_path: Path, record_count: int = 1_000):
    return generate_dataset(
        tmp_path, GeneratorConfig(seed=17, record_count=record_count), dataset_id=DATASET_ID
    )


def _experiment_manifest(
    dataset_manifest, *, target_records_per_task: int = 250
) -> ExperimentManifest:
    return ExperimentManifest(
        schema_name="forge.experiment-manifest",
        schema_version=1,
        experiment_id="test-experiment",
        dataset=ExperimentDatasetRef(
            dataset_id=dataset_manifest.dataset_id,
            content_sha256=dataset_manifest.content_sha256,
        ),
        partitioning=ExperimentPartitioning(
            policy="contiguous-record-ranges",
            policy_version=1,
            target_records_per_task=target_records_per_task,
        ),
        kernel=ExperimentKernelSpec(
            kernel_id="forge.event-counts",
            kernel_version="1.0.0",
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
            schema_id="forge.event-counts-result", schema_version=1, canonical_merge="ordinal"
        ),
    )


# --- derive_partition_seed ----------------------------------------------------


def test_derive_partition_seed_is_deterministic() -> None:
    first = derive_partition_seed(42, "map", "p-000000")
    second = derive_partition_seed(42, "map", "p-000000")
    assert first == second


def test_derive_partition_seed_varies_with_each_input() -> None:
    base = derive_partition_seed(42, "map", "p-000000")
    assert derive_partition_seed(43, "map", "p-000000") != base
    assert derive_partition_seed(42, "merge", "p-000000") != base
    assert derive_partition_seed(42, "map", "p-000001") != base


# --- plan_run_partitions -------------------------------------------------------


def test_plan_run_partitions_populates_seed_and_covers_all_records(tmp_path: Path) -> None:
    dataset_manifest = _generate(tmp_path, 1_000)
    experiment = _experiment_manifest(dataset_manifest, target_records_per_task=250)

    partitions = plan_run_partitions(dataset_manifest, experiment, run_seed=42)

    assert len(partitions) == 4
    assert all(p.partition_seed is not None for p in partitions)
    assert sum(p.record_count for p in partitions) == 1_000


def test_plan_run_partitions_is_deterministic(tmp_path: Path) -> None:
    dataset_manifest = _generate(tmp_path, 500)
    experiment = _experiment_manifest(dataset_manifest, target_records_per_task=100)

    first = plan_run_partitions(dataset_manifest, experiment, run_seed=7)
    second = plan_run_partitions(dataset_manifest, experiment, run_seed=7)
    assert first == second


def test_plan_run_partitions_rejects_dataset_id_mismatch(tmp_path: Path) -> None:
    dataset_manifest = _generate(tmp_path, 100)
    experiment = _experiment_manifest(dataset_manifest)
    tampered = experiment.model_copy(
        update={
            "dataset": ExperimentDatasetRef(
                dataset_id="a-different-dataset",
                content_sha256=dataset_manifest.content_sha256,
            )
        }
    )
    with pytest.raises(PlanningError, match="dataset_id"):
        plan_run_partitions(dataset_manifest, tampered, run_seed=1)


def test_plan_run_partitions_rejects_content_digest_mismatch(tmp_path: Path) -> None:
    dataset_manifest = _generate(tmp_path, 100)
    experiment = _experiment_manifest(dataset_manifest)
    tampered = experiment.model_copy(
        update={
            "dataset": ExperimentDatasetRef(
                dataset_id=dataset_manifest.dataset_id,
                content_sha256="0" * 64,
            )
        }
    )
    with pytest.raises(PlanningError, match="content_sha256"):
        plan_run_partitions(dataset_manifest, tampered, run_seed=1)
