# Appendix J - Benchmark Runner, Raw Evidence, and Analysis Skeleton

## 408. Benchmark Manifest Example

    schema: forge.benchmark-manifest
    schema_version: 1
    benchmark_id: worker-scaling-instrument-stats-v1
    question: >
      How does end-to-end throughput and efficiency change from one to eight
      local workers for a fixed compute-oriented aggregation workload?

    source:
      tag: v1.0.0
      commit: <full sha>
      build_profile: release

    inputs:
      dataset_manifest: benchmarks/datasets/compute-10m.json
      experiment_manifest: benchmarks/experiments/instrument-stats.json
      expected_dataset_sha256: <digest>

    matrix:
      worker_count: [1, 2, 4, 8]
      engine: [python, cpp]
      target_records_per_task: [250000]

    protocol:
      transport: unix
      coordinator_database: sqlite-wal-full
      warmup_runs: 2
      measured_runs: 10
      randomized_order: true
      cooldown_seconds: 5
      failure_policy: abort-cell

    controls:
      cpu_affinity: "2-9"
      governor: performance
      background_process_policy: documented
      drop_filesystem_cache: false
      dataset_cache_state: warm

    metrics:
      - elapsed_seconds
      - records_per_second
      - worker_cpu_seconds
      - coordinator_cpu_seconds
      - peak_total_rss_bytes
      - bytes_read
      - bytes_written
      - scheduler_assignments
      - database_write_seconds
      - merge_seconds

## 409. Raw Trial Record

    {
      "schema_version": 1,
      "benchmark_id": "worker-scaling-instrument-stats-v1",
      "cell_id": "workers=4,engine=cpp,partition=250000",
      "trial_index": 7,
      "trial_order": 19,
      "source_commit": "<sha>",
      "environment_sha256": "<digest>",
      "configuration_sha256": "<digest>",
      "dataset_sha256": "<digest>",
      "experiment_sha256": "<digest>",
      "started_at_utc": "<time>",
      "warmup": false,
      "status": "success",
      "parameters": {
        "worker_count": 4,
        "engine": "cpp",
        "target_records_per_task": 250000
      },
      "results": {
        "records": 10000000,
        "elapsed_seconds": 1.234567,
        "records_per_second": 8100005.2,
        "coordinator_cpu_seconds": 0.18,
        "worker_cpu_seconds": 4.21,
        "peak_total_rss_bytes": 734003200,
        "bytes_read": 320000000,
        "bytes_written": 125000,
        "merge_seconds": 0.041,
        "retries": 0
      },
      "canonical_result_sha256": "<digest>",
      "raw_artifacts": {
        "metrics": "trials/.../metrics.jsonl",
        "logs": "trials/.../logs.jsonl",
        "perf_stat": "trials/.../perf-stat.txt"
      }
    }

## 410. Environment Manifest Fields

**Table 143 --- Benchmark environment manifest.**

  ----------------------------------------------------------------------------------------------------------------
  Category                       Fields
  ------------------------------ ---------------------------------------------------------------------------------
  Host                           stable host label, physical/virtual/container, model, firmware if relevant

  CPU                            model, sockets, cores, threads, cache, frequency policy, affinity, turbo policy

  Memory                         capacity, speed if known, NUMA topology, swap policy

  Storage                        device/model/type, filesystem, mount options, free space, cache state policy

  Operating system               distribution, kernel, libc, relevant limits

  Toolchain                      Python, compiler, CMake, pybind11, optimization and link flags

  Dependencies                   lock digest and installed package report

  Source                         tag, full commit, dirty state, submodule/dependency source identities

  Runtime config                 worker/process/queue/lease/SQLite/protocol/native settings

  Background conditions          load, power source, thermal state, monitoring overhead
  ----------------------------------------------------------------------------------------------------------------

## 411. Analysis Skeleton

    from __future__ import annotations

    import json
    from pathlib import Path
    from statistics import median
    from typing import Any


    def load_trials(path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid JSON on line {line_number}: {exc}"
                    ) from exc
                if row.get("status") == "success" and not row.get("warmup", False):
                    rows.append(row)
        if not rows:
            raise ValueError("no successful measured trials")
        return rows


    def summarize_by_cell(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row["cell_id"], []).append(row)

        summaries: list[dict[str, Any]] = []
        for cell_id, trials in sorted(grouped.items()):
            throughputs = [
                float(trial["results"]["records_per_second"])
                for trial in trials
            ]
            elapsed = [
                float(trial["results"]["elapsed_seconds"])
                for trial in trials
            ]
            summaries.append(
                {
                    "cell_id": cell_id,
                    "n": len(trials),
                    "median_records_per_second": median(throughputs),
                    "min_records_per_second": min(throughputs),
                    "max_records_per_second": max(throughputs),
                    "median_elapsed_seconds": median(elapsed),
                    "environment_sha256": unique_value(
                        trials, "environment_sha256"
                    ),
                    "source_commit": unique_value(trials, "source_commit"),
                }
            )
        return summaries

## 412. Scaling Calculations

    T(1) = median elapsed time with one worker
    T(p) = median elapsed time with p workers

    speedup(p) = T(1) / T(p)
    parallel_efficiency(p) = speedup(p) / p

    throughput(p) = processed records / T(p)
    throughput_gain(p) = throughput(p) / throughput(1)

    Report both elapsed-time speedup and absolute throughput. If task count, input,
    engine, cache state, or result semantics change, it is not a strong-scaling cell.

## 413. Benchmark Validity Checklist

- The benchmark question is written before trials and names the decision it informs.
- Input, source, configuration, and environment are immutable or hashed.
- Warm-up and cache policy are explicit and consistent across cells.
- Cell execution order is randomized or counterbalanced to reduce thermal/time trend bias.
- Failed trials are preserved and classified rather than deleted silently.
- Correctness digest is checked for every successful trial.
- Timing boundaries exclude setup only when setup exclusion is documented and meaningful.
- Child-process, coordinator, and whole-system resource measurements use a defined aggregation method.
- Raw evidence is append-only; summaries and plots are regenerated outputs.
- Outlier policy is written before exclusion and both included/excluded results can be audited.
- Claims use a statistic supported by the trial design and include sample count.
- Performance changes are profiled before attribution.

## 414. Negative Experiment Record

    # Experiment: <name>

    ## Hypothesis
    A precise prediction, for example: replacing socket-transferred batch bytes with
    shared memory will improve end-to-end throughput by at least 15% when serialization
    and copy time exceed 25% of baseline elapsed time.

    ## Baseline evidence
    Profile, workload, source tag, environment, and measured component share.

    ## Change
    Implementation and configuration difference. State whether semantics changed.

    ## Results
    Raw evidence links, summary statistic, uncertainty, memory/CPU effects, and output
    digest equality.

    ## Conclusion
    Supported, not supported, or inconclusive. Do not turn a neutral result into a
    success through a different metric selected afterward.

    ## Decision
    Keep, revert, defer, or redesign. Explain maintenance and complexity cost.
