# Week 4 Checklist — Single-Process Experiment Engine and Reference Kernels (Gate A)

Must-have outcomes from `docs/spec/part-17-roadmap.md` §274, with a pointer to the
code or test that proves each one.

| Must-have | Status | Evidence |
|---|---|---|
| Kernel registry: stable ids, versions, parameter validation, declared result schemas | Done | [`forge/kernels/base.py`](../../forge/kernels/base.py) — `Kernel` protocol, `KernelRegistry` |
| At least three reference kernels: event counts, keyed aggregation, rolling stats/checksum | Done | [`event_counts.py`](../../forge/kernels/event_counts.py), [`instrument_sums.py`](../../forge/kernels/instrument_sums.py), [`checksum_chain.py`](../../forge/kernels/checksum_chain.py) |
| Sequential partition execution, attempt-like local outputs, canonical-order merge, result manifest | Done | [`forge/planner/reference_engine.py`](../../forge/planner/reference_engine.py) — `run_reference_experiment` |
| Normalize run metadata so nondeterministic timestamps/paths don't affect the result digest | Done | `canonical_result_digest = Digest.of_bytes(final_result)`, computed before `ReferenceResultManifest` (which carries `created_utc`) is even built — see module docstring |
| Replay, deterministic-output, invalid-parameter, merge-order, differential tests | Done | [`tests/python/kernels/`](../../tests/python/kernels/), [`tests/python/planner/`](../../tests/python/planner/) |

## End-of-week acceptance demonstration

Per §274: "Run the same experiment twice, compare normalized output bytes and
digests, then compare a generated workload against a slow independent
implementation."

```
uv run --extra test pytest tests/python -q
```

241 tests pass. `test_running_the_same_experiment_twice_produces_the_same_digest`
and `test_publishes_a_result_manifest_and_partition_files` cover the first half;
`test_event_counts_matches_a_brute_force_oracle` and
`test_instrument_sum_matches_a_brute_force_oracle` cover the second — each recomputes
its result directly from every record with no partitioning at all, independently of
`forge.planner`/`forge.kernels`' partition-and-merge path, and asserts equality.

## Design notes worth flagging on review

- **The Kernel protocol is a synthesis, not a spec quote.** §20's inline sketch
  (`run_partition`/`merge`) and Appendix B §356's registry code
  (`execute_batches` over `memoryview` batches, no merge step) disagree with each
  other and neither is complete alone. `forge/kernels/base.py` combines them:
  `execute_partition`/`merge` (§20's two-phase shape) operating on `EventRecord`
  objects, not raw `memoryview` batches — the batch/buffer-protocol abstraction is
  explicitly what the C++ boundary needs (Week 13), and committing to it now would
  jump ahead of the critical path (§41: "measure the Python implementation before
  choosing the C++ boundary").
- **The checksum-chain kernel is deliberately order-sensitive**, unlike the other
  two (which are associative/commutative and therefore partition-shape-invariant).
  `test_associative_kernel_digest_is_invariant_to_partition_boundaries` and
  `test_checksum_chain_digest_changes_with_partition_boundaries` together are the
  sharpest evidence that the engine's merge step actually respects canonical
  ordinal order (§24) rather than silently normalizing every kernel to the same
  answer regardless of task granularity.
- **`forge.planner` now has its first real code**, closing two things Week 2/3 left
  open: `plan_run_partitions` cross-checks an experiment's declared
  `dataset.content_sha256` against the actual loaded dataset manifest (§17's
  "reject... inconsistent dataset digests," undoable until both manifests exist
  together), and `derive_partition_seed` fills in the `partition_seed` field Week
  3's dataset-only partition index deliberately left `None`.
- **Package placement**: the reference engine lives in `forge/planner/`, not a new
  top-level package. The component table (§38) doesn't name a specific home for
  "single-process engine," and inventing a 16th package for one week's work seemed
  worse than placing it beside the partitioning code it's built directly on top of.
  Flagged here as a judgment call, not a spec citation.

## Explicitly deferred (out of scope for Week 4)

Streaming kernel interface and the tiny HTML/Markdown run report are both stretch
outcomes and were skipped. Everything coordinator/metadata/protocol-shaped —
durable run state, leases, real attempts, restart recovery — is Week 5+ and
untouched; today's "attempt-like local outputs" are plain files with no lease or
commit semantics behind them.
