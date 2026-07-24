# ADR-0002: At-least-once execution with exactly-once visible result publication

Status: Proposed

## Context

§14 (Semantic Design Principles) states the guarantee's shape directly: "Task
execution may repeat; visible result publication must be conditional and idempotent,"
and "Every semantic guarantee must name its boundary. Forge can guarantee one
committed result record per task without guaranteeing that external side effects run
only once."

§4 (Explicit Non-Goals) rules out the stronger alternative explicitly: "Exactly-once
physical execution. Retries may execute a task more than once; the guarantee concerns
result visibility and commit state."

§26 (Idempotency and Side-Effect Boundary) grounds why physical exactly-once is not
attempted: "Exactly-once visible result publication does not make arbitrary kernel
side effects exactly once. A retry may execute the same partition again. Therefore
the baseline kernel contract is side-effect-free except for attempt-scoped staged
output and structured telemetry." It also specifies the supporting idempotency rules:
submission accepts an optional client request ID; task-finish messages are idempotent
for the same attempt and digest, with a conflicting second digest being an invariant
violation; worker registration/heartbeat messages may repeat without creating
duplicate workers or leases; artifact promotion is conditional on durable task state
using attempt-specific staging names; cleanup is idempotent.

§27 (Result Visibility and Commit Semantics) describes the mechanism: a worker
finalizes an attempt-specific output, computes its digest, and reports a
staged-result descriptor; the coordinator validates the descriptor and executes a
transaction that checks task state, cancellation, fencing policy, artifact existence,
and digest before recording the winning attempt.

§31 (Core Invariants) encodes this as INV-001 ("At most one committed attempt exists
for a task"), INV-002 ("A committed task has a committed artifact reference and
matching digest"), INV-006 ("A stale generation cannot renew a lease or become
committed"), and INV-016 ("A metadata transaction never points at an unverified or
missing committed artifact").

The question this ADR must settle: what is the execution/publication guarantee Forge
offers, and what fencing and commit mechanism enforces it when a task attempt is
retried after a crash, a lease expiry, or a network partition produces a duplicate
completion.

## Alternatives to consider

- **At-least-once execution, exactly-once visible commit** (the guarantee described
  throughout §14/§26/§27/§31): retries may re-execute a task, but a coordinator-owned
  conditional transaction, guarded by a monotonic fencing epoch (INV-005, INV-006),
  ensures only one attempt's result is ever recorded as the task's committed result.
- **Exactly-once physical execution**: would require distributed consensus or
  external transactional side-effect coordination to guarantee a kernel runs at most
  once even across worker crashes. Explicitly ruled out by §4 as a non-goal, and by
  §4's related non-goal on Byzantine fault tolerance and multi-leader consensus.
- **At-most-once execution**: a failed or unresponsive attempt is never retried,
  trading fault tolerance for a simpler commit rule. Inconsistent with §31 INV-012
  (retry count tracking) and with the fault-tolerance goals in §3 (demonstrate
  at-least-once execution, leases, fencing tokens).
- **Client-side deduplication without a coordinator-enforced commit**: workers or
  clients decide which result "wins" by convention (e.g., last write wins on a shared
  path) instead of a durable, transactional coordinator decision. Inconsistent with
  §27's requirement that "the semantic authority remains the metadata commit record"
  and with INV-016.

## Decision

TODO (project owner).

## Consequences

TODO (project owner).
