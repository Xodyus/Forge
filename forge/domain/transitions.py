"""Legal state transitions for runs, tasks, attempts, and workers.

Run and task transitions are transcribed from §29 Table 16 and §21 Table 12. Worker
transitions are synthesized from §30 Table 17's per-state notes (that table lists
meanings, not a "next states" column) plus the session/durable-identity distinction
in the glossary — a worker's states form a cycle (a session can be lost and later
reconnect under the same durable ``worker_id``, or a quarantined worker can be
explicitly returned to service), unlike the run/task machines, which are DAGs that
end in one of several terminal states. Attempt transitions extend the synthesized
``AttemptState`` enum documented in :mod:`forge.domain.states`.

Making COMMITTED/FAILED/CANCELLED (task) and the run's terminal states have zero
legal successors is not just tidiness: it is the mechanism that enforces §28's
"commit wins" cancellation race rule (Table 15, row "Cancel races with commit
transaction") and INV-017 ("A task cannot transition from COMMITTED, FAILED, or
CANCELLED back to an executable state"). Once a commit transaction lands, the empty
transition set makes a later cancellation transition on that task illegal by
construction rather than by a runtime policy check.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import TypeVar

from forge.domain.errors import IllegalTransitionError
from forge.domain.states import AttemptState, RunState, TaskState, WorkerState

_StateT = TypeVar("_StateT", bound=Enum)

RUN_TRANSITIONS: Mapping[RunState, frozenset[RunState]] = {
    RunState.SUBMITTED: frozenset({RunState.PLANNING, RunState.REJECTED, RunState.CANCELLED}),
    RunState.PLANNING: frozenset({RunState.RUNNING, RunState.REJECTED, RunState.CANCELLED}),
    RunState.RUNNING: frozenset({RunState.MERGING, RunState.FAILED, RunState.CANCELLING}),
    RunState.MERGING: frozenset({RunState.SUCCEEDED, RunState.FAILED, RunState.CANCELLING}),
    RunState.CANCELLING: frozenset({RunState.CANCELLED, RunState.FAILED}),
    RunState.SUCCEEDED: frozenset(),
    RunState.FAILED: frozenset(),
    RunState.CANCELLED: frozenset(),
    RunState.REJECTED: frozenset(),
}

TASK_TRANSITIONS: Mapping[TaskState, frozenset[TaskState]] = {
    TaskState.PENDING: frozenset({TaskState.LEASED, TaskState.CANCELLED, TaskState.FAILED}),
    TaskState.LEASED: frozenset(
        {
            TaskState.RUNNING,
            TaskState.PENDING,  # lease expired before acknowledgement, retry remains
            TaskState.CANCELLED,
            TaskState.FAILED,
        }
    ),
    TaskState.RUNNING: frozenset(
        {
            TaskState.STAGED,
            TaskState.PENDING,  # retryable failure or lease expiry
            TaskState.CANCELLED,
            TaskState.FAILED,
        }
    ),
    TaskState.STAGED: frozenset(
        {
            TaskState.COMMITTED,
            TaskState.PENDING,  # commit could not proceed, retry policy permits
            TaskState.CANCELLED,
            TaskState.FAILED,
        }
    ),
    TaskState.COMMITTED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.CANCELLED: frozenset(),
}

WORKER_TRANSITIONS: Mapping[WorkerState, frozenset[WorkerState]] = {
    WorkerState.REGISTERING: frozenset(
        {WorkerState.IDLE, WorkerState.LOST, WorkerState.QUARANTINED}
    ),
    WorkerState.IDLE: frozenset(
        {WorkerState.LEASED, WorkerState.DRAINING, WorkerState.LOST, WorkerState.QUARANTINED}
    ),
    WorkerState.LEASED: frozenset(
        {
            WorkerState.BUSY,
            WorkerState.IDLE,  # lease given up before execution acknowledged
            WorkerState.DRAINING,
            WorkerState.LOST,
            WorkerState.QUARANTINED,
        }
    ),
    WorkerState.BUSY: frozenset(
        {WorkerState.IDLE, WorkerState.DRAINING, WorkerState.LOST, WorkerState.QUARANTINED}
    ),
    WorkerState.DRAINING: frozenset({WorkerState.LOST}),
    WorkerState.LOST: frozenset({WorkerState.REGISTERING}),  # reconnect, same worker_id
    WorkerState.QUARANTINED: frozenset({WorkerState.REGISTERING}),  # explicit operator action
}

ATTEMPT_TRANSITIONS: Mapping[AttemptState, frozenset[AttemptState]] = {
    AttemptState.ASSIGNED: frozenset(
        {
            AttemptState.RUNNING,
            AttemptState.EXPIRED,
            AttemptState.CANCELLED,
            AttemptState.REJECTED_STALE,
            AttemptState.FAILED,
        }
    ),
    AttemptState.RUNNING: frozenset(
        {
            AttemptState.STAGED,
            AttemptState.FAILED,
            AttemptState.EXPIRED,
            AttemptState.CANCELLED,
            AttemptState.REJECTED_STALE,
        }
    ),
    AttemptState.STAGED: frozenset(
        {
            AttemptState.COMMITTED,
            AttemptState.FAILED,
            AttemptState.EXPIRED,
            AttemptState.CANCELLED,
            AttemptState.REJECTED_STALE,
        }
    ),
    AttemptState.COMMITTED: frozenset(),
    AttemptState.FAILED: frozenset(),
    AttemptState.EXPIRED: frozenset(),
    AttemptState.CANCELLED: frozenset(),
    AttemptState.REJECTED_STALE: frozenset(),
}


def _require_transition(
    transitions: Mapping[_StateT, frozenset[_StateT]],
    current: _StateT,
    target: _StateT,
    *,
    allow_idempotent: bool,
) -> None:
    if current == target and allow_idempotent:
        return
    if target not in transitions[current]:
        raise IllegalTransitionError(
            f"cannot transition {type(current).__name__} {current} -> {target}"
        )


def require_run_transition(
    current: RunState, target: RunState, *, allow_idempotent: bool = True
) -> None:
    _require_transition(RUN_TRANSITIONS, current, target, allow_idempotent=allow_idempotent)


def require_task_transition(
    current: TaskState, target: TaskState, *, allow_idempotent: bool = True
) -> None:
    _require_transition(TASK_TRANSITIONS, current, target, allow_idempotent=allow_idempotent)


def require_worker_transition(
    current: WorkerState, target: WorkerState, *, allow_idempotent: bool = True
) -> None:
    _require_transition(WORKER_TRANSITIONS, current, target, allow_idempotent=allow_idempotent)


def require_attempt_transition(
    current: AttemptState, target: AttemptState, *, allow_idempotent: bool = True
) -> None:
    _require_transition(ATTEMPT_TRANSITIONS, current, target, allow_idempotent=allow_idempotent)
