# State Machines

Source of truth: [`forge/domain/states.py`](../../forge/domain/states.py) (enum
members) and [`forge/domain/transitions.py`](../../forge/domain/transitions.py)
(allowed-transition maps and `require_*_transition()` guards). This document is a
human-readable rendering of those two modules, not an independent definition — if
they disagree, the code is authoritative and this file is stale.

Run and task tables are transcribed directly from the spec. The worker and attempt
tables have no literal "next states" table in Part II and are documented design
decisions synthesized from prose; see the module docstrings for exactly what each is
based on.

## Run state machine (§29 Table 16)

| From | Legal next states |
|---|---|
| SUBMITTED | PLANNING, REJECTED, CANCELLED |
| PLANNING | RUNNING, REJECTED, CANCELLED |
| RUNNING | MERGING, FAILED, CANCELLING |
| MERGING | SUCCEEDED, FAILED, CANCELLING |
| CANCELLING | CANCELLED, FAILED |
| SUCCEEDED | *(terminal)* |
| FAILED | *(terminal)* |
| CANCELLED | *(terminal)* |
| REJECTED | *(terminal)* |

## Task state machine (§21 Table 12)

| From | Legal next states |
|---|---|
| PENDING | LEASED, CANCELLED, FAILED |
| LEASED | RUNNING, PENDING (lease expired before ack), CANCELLED, FAILED |
| RUNNING | STAGED, PENDING (retryable failure/expiry), CANCELLED, FAILED |
| STAGED | COMMITTED, PENDING (commit could not proceed, retry allowed), CANCELLED, FAILED |
| COMMITTED | *(terminal)* |
| FAILED | *(terminal, unless explicit administrative reset)* |
| CANCELLED | *(terminal)* |

COMMITTED/FAILED/CANCELLED having **zero** legal successors is the mechanism, not
just documentation, for two rules: INV-017 ("a task cannot transition from
COMMITTED, FAILED, or CANCELLED back to an executable state") and §28 Table 15's
"commit wins" cancellation race — once a commit transaction lands, a later
cancellation transition on that task is illegal by construction. See
`test_committed_task_cannot_be_retroactively_cancelled` in
[`tests/python/domain/test_transitions.py`](../../tests/python/domain/test_transitions.py).

## Worker state machine (synthesized from §30 Table 17's per-state notes)

Unlike run/task, this is not a DAG ending in a terminal state — a worker's *durable
identity* can outlive any one session, so LOST and QUARANTINED both cycle back to
REGISTERING (reconnect, or an explicit operator/test action) rather than terminating.

| From | Legal next states |
|---|---|
| REGISTERING | IDLE, LOST, QUARANTINED |
| IDLE | LEASED, DRAINING, LOST, QUARANTINED |
| LEASED | BUSY, IDLE (lease given up before execution ack), DRAINING, LOST, QUARANTINED |
| BUSY | IDLE, DRAINING, LOST, QUARANTINED |
| DRAINING | LOST |
| LOST | REGISTERING *(reconnect under the same durable `worker_id`)* |
| QUARANTINED | REGISTERING *(explicit operator/test action only)* |

## Attempt state machine (synthesized from Appendix B §353 + §21–§23, §27 prose)

Part II has no explicit attempt-state table; `AttemptState` and this table extend
Appendix B's skeleton enum using the lease/retry/commit semantics described in
§21–§23 and §27. Treat this as a documented design decision to revisit once
coordinator work (Week 5+) exercises it against real lease/commit code.

| From | Legal next states |
|---|---|
| ASSIGNED | RUNNING, EXPIRED, CANCELLED, REJECTED_STALE, FAILED |
| RUNNING | STAGED, FAILED, EXPIRED, CANCELLED, REJECTED_STALE |
| STAGED | COMMITTED, FAILED, EXPIRED, CANCELLED, REJECTED_STALE |
| COMMITTED | *(terminal)* |
| FAILED | *(terminal)* |
| EXPIRED | *(terminal)* |
| CANCELLED | *(terminal)* |
| REJECTED_STALE | *(terminal)* |

## Idempotent self-transitions

Every `require_*_transition()` guard accepts `allow_idempotent: bool = True`: a
state transitioning to itself always succeeds unless a caller explicitly opts out
with `allow_idempotent=False`. This exists because §26 requires task-finish and
heartbeat messages to be idempotent for retried/duplicated calls — a repeated
message that reports the same state a task is already in must not be treated as an
illegal transition.
