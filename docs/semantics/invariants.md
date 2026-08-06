# Invariant Matrix

Source: §31 Table 18 (`docs/spec/part-02-execution-model.md`). Ten of the twenty
invariants are checkable today from domain objects alone and are implemented as
pure assertion helpers in
[`forge/domain/invariants.py`](../../forge/domain/invariants.py), each with a unit
test in
[`tests/python/domain/test_invariants.py`](../../tests/python/domain/test_invariants.py).
The other ten need durable metadata, a running coordinator, live queues, or a real
planner/kernel — components that don't exist until later weeks per the roadmap
(`docs/spec/part-17-roadmap.md`). Those get a named future test location instead of
a stub function that can't observe what it's supposed to check.

| ID | Invariant | Owning layer | Status |
|---|---|---|---|
| INV-001 | At most one committed attempt exists for a task. | `forge.domain` | Implemented — `assert_at_most_one_committed_attempt` |
| INV-002 | A committed task has a committed artifact reference and matching digest. | `forge.domain` | Implemented — `assert_committed_task_has_matching_artifact` |
| INV-003 | A run is SUCCEEDED only when all required tasks and final merge are committed and verified. | `forge.coordinator` | Planned — coordinator run-completion transaction (Week 8, E05-06/E05-07) |
| INV-004 | A task attempt belongs to exactly one task and one worker lease generation. | `forge.domain` | Implemented — `assert_attempt_belongs_to_one_task_and_generation` |
| INV-005 | Fencing generations for a task increase monotonically. | `forge.domain` | Implemented — `assert_fencing_generations_increase` |
| INV-006 | A stale generation cannot renew a lease or become committed. | `forge.domain` | Implemented — `assert_generation_not_stale` |
| INV-007 | A cancelled or terminal run does not create new leases. | `forge.coordinator` | Planned — cancellation propagation (Week 7–8, E05-06) |
| INV-008 | A partition plan is immutable after the run enters RUNNING. | `forge.coordinator` | Planned — durable task planning (Week 5, E03-04) |
| INV-009 | Committed artifact paths are immutable and never reused for different content. | `forge.domain` | Implemented — `assert_committed_path_not_reused` |
| INV-010 | Attempt staging paths are unique and cannot overwrite another attempt. | `forge.domain` | Implemented — `assert_staging_paths_unique` |
| INV-011 | Every state transition records a durable reason or source event. | `forge.coordinator` / `forge.metadata` | Planned — transaction wrapper (Week 5, E03-02) |
| INV-012 | Retry count equals the number of created attempts minus the initial attempt, subject to explicit administrative operations. | `forge.domain` | Implemented — `assert_retry_count_consistent` |
| INV-013 | A worker cannot hold more active leases than its accepted capacity. | `forge.worker` / `forge.coordinator` | Planned — bounded assignment queue / scheduler queries (Week 6–7, E04-02/E03-06) |
| INV-014 | Queue sizes never exceed configured hard bounds. | `forge.worker` / `forge.transport` | Planned — bounded queues (Week 6, 9–10, E04-02/E06-06) |
| INV-015 | Canonical result digests exclude nondeterministic run metadata. | `forge.planner` / reference engine | Planned — normalized run/result manifests (Week 4, E02-07) |
| INV-016 | A metadata transaction never points at an unverified or missing committed artifact. | `forge.coordinator` / `forge.artifacts` | Planned — staged artifact registration / commit transaction (Week 7, E05-04/E05-05) |
| INV-017 | A task cannot transition from COMMITTED, FAILED, or CANCELLED back to an executable state. | `forge.domain` | Implemented — `assert_no_transition_from_terminal_task_state`, and structurally enforced by `TASK_TRANSITIONS`' empty terminal successor sets (`forge/domain/transitions.py`) |
| INV-018 | The planner creates complete, non-overlapping coverage of the declared dataset slice. | `forge.planner` | Planned — deterministic partition planner (Week 3–4, E02-04) |
| INV-019 | The reference and distributed paths share the manifest and partition contracts but not an implementation that could mask the same bug. | cross-cutting | Planned — differential tests between the reference executor (Week 4, E02-08) and the distributed path (Week 6+, E04) |
| INV-020 | All schema and protocol versions are validated before their fields are interpreted. | `forge.domain` | Implemented — `assert_schema_version_supported`, used by every manifest's `schema_version` validator in `forge/domain/manifests.py` and `forge/datasets/manifest.py` |
