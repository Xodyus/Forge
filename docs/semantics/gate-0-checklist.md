# Gate 0 Checklist — Week 2

Must-have outcomes from `docs/spec/part-17-roadmap.md` §272, with a pointer to the
code or test that proves each one.

| Must-have | Status | Evidence |
|---|---|---|
| Typed models for dataset, experiment, and run manifests | Done | [`forge/domain/manifests.py`](../../forge/domain/manifests.py) (experiment, run), [`forge/datasets/manifest.py`](../../forge/datasets/manifest.py) (dataset) |
| Transition tables for run, task, attempt, lease, and worker state | Done | [`forge/domain/transitions.py`](../../forge/domain/transitions.py), rendered in [`state-machines.md`](state-machines.md). Lease state is carried by `LeaseGrant` (`forge/domain/descriptors.py`) plus the fencing invariants (INV-005/006) rather than a separate enum — a lease doesn't have life-cycle states of its own beyond "current" vs. "stale," which fencing-epoch comparison already captures. |
| 32-byte synthetic event record, file header, endianness, version, record count, checksum behavior | Done | [`forge/datasets/format.py`](../../forge/datasets/format.py) — encode/decode only, no generator (Week 3) |
| Cross-component invariants mapped to a planned test | Done | [`invariants.md`](invariants.md); ten implemented now in `forge/domain/invariants.py`, ten mapped to a named future week |
| Canonical example manifests and invalid fixtures (unknown fields, bad versions, duplicate identifiers, path traversal, checksum mismatch) | Done | [`tests/fixtures/manifests/valid/`](../../tests/fixtures/manifests/valid/), [`tests/fixtures/manifests/invalid/`](../../tests/fixtures/manifests/invalid/) |

## End-of-week acceptance demonstration

Per §272: "Validate good fixtures, reject bad fixtures with stable error codes, and
walk through a task from pending to committed and through lease expiry to retry."

```
uv run --extra test pytest tests/python -q
```

174 tests pass, covering: every legal transition in all four state machines plus
representative illegal ones (including PENDING → LEASED → RUNNING → STAGED →
COMMITTED and LEASED → PENDING on lease expiry); every `valid/` fixture parsing and
round-tripping through canonical bytes; every `invalid/` fixture raising a
`pydantic.ValidationError` identifying which check failed.

## Explicitly deferred (out of scope for Week 2)

Stretch outcomes (schema-doc generation from typed models, an exhaustive
legal/illegal transition explorer) were skipped — must-haves only, per the roadmap's
own must-have/stretch split. Dataset generator, partition planner, sequential
reference executor, SQLite schema, coordinator, and protocol frames are untouched;
`forge/planner`, `forge/coordinator`, `forge/metadata`, `forge/protocol` remain stub
packages for their respective later weeks.
