# Week 3 Checklist — Deterministic Dataset Generator and Reference Reader

Must-have outcomes from `docs/spec/part-17-roadmap.md` §273, with a pointer to the
code or test that proves each one.

| Must-have | Status | Evidence |
|---|---|---|
| Seeded synthetic event generator, fixed distributions, explicit generator-version metadata | Done | [`forge/datasets/generator.py`](../../forge/datasets/generator.py) — `GeneratorConfig` + `generate_records`; `GENERATOR_ID`/`GENERATOR_VERSION` recorded in every manifest's `created_by` |
| Binary file headers and fixed-width records, checked arithmetic, atomic publication | Done | [`forge/datasets/atomic.py`](../../forge/datasets/atomic.py) (temp file + fsync + `os.replace`, POSIX directory fsync where supported); header/record packing from Week 2's [`forge/datasets/format.py`](../../forge/datasets/format.py) |
| Python reader validating magic, version, lengths, record count, checksum, event fields | Done | [`forge/datasets/reader.py`](../../forge/datasets/reader.py) — `DatasetFileReader.open()` (header + length), `verify_payload_digest()` (checksum), `iter_records()` (per-record field validation via `EventRecord.unpack`) |
| Deterministic partitioning by record range, partition descriptors with byte offsets and digests | Done | [`forge/datasets/partitioning.py`](../../forge/datasets/partitioning.py) — `plan_dataset_partitions`, pure function, `PartitionDescriptor.partition_seed=None` (deferred to `forge.planner`, Week 4 — see docstring on `PartitionDescriptor`) |
| Golden-file, truncation, corruption, boundary, round-trip tests | Done | [`tests/python/datasets/test_generator.py`](../../tests/python/datasets/test_generator.py), [`test_reader.py`](../../tests/python/datasets/test_reader.py), [`test_partitioning.py`](../../tests/python/datasets/test_partitioning.py) |

## End-of-week acceptance demonstration

Per §273: "Generate a dataset twice from the same manifest, compare digests, inspect
records, corrupt one byte, and show a precise validation failure."

```
uv run --extra test pytest tests/python -q
```

202 tests pass. The demo itself (`generate_dataset` called twice from the same
`GeneratorConfig` produces byte-identical files and manifests; flipping one payload
byte is caught by `verify_payload_digest()` with a checksum-mismatch error naming
the file and both digests) is exercised directly in
`test_generating_twice_from_the_same_config_is_byte_identical` and
`test_corrupted_payload_byte_passes_open_but_fails_digest_check`.

## Design notes worth flagging on review

- The generator buffers all records in memory and hashes once before writing,
  because the file header must carry the payload's digest and the header is written
  *before* the payload in the file — see the module docstring in `generator.py`.
  This is a reference-scale choice; a streaming variant that writes a placeholder
  header, hashes while streaming, then seeks back to patch the header is deferred to
  the benchmarking weeks (E10) if a real record count ever makes buffering matter.
- `plan_dataset_partitions` is dataset-only and does not populate
  `PartitionDescriptor.partition_seed`, because §19 defines that field as derived
  from a *run* seed, which doesn't exist until an experiment/run is created
  (`forge.planner`, Week 4). This required loosening `partition_seed` from a
  required to an optional field on `PartitionDescriptor` (a small, low-risk revision
  to Week 2's domain model, not a new invariant or contract).
- Directory-entry fsync in `write_atomic` is skipped on Windows (`os.name != "posix"`)
  — there is no Windows equivalent of opening a directory as a file descriptor, and
  `os.replace` is already atomic there. The spec's target deployment is Linux;
  the guard just keeps local development on Windows from crashing on every write.

## Explicitly deferred (out of scope for Week 3)

The dataset inspection CLI (sample/validate/summarize) and memory-mapped reader are
both stretch outcomes and were skipped. Partition *task* planning — reconciling this
dataset-only partition index with an experiment's `target_records_per_task` and a
run seed to produce fully-populated `PartitionDescriptor`s — is `forge.planner`,
Week 4, and untouched.
