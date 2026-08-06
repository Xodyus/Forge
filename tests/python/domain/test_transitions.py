import pytest
from forge.domain.errors import IllegalTransitionError
from forge.domain.states import AttemptState, RunState, TaskState, WorkerState
from forge.domain.transitions import (
    ATTEMPT_TRANSITIONS,
    RUN_TRANSITIONS,
    TASK_TRANSITIONS,
    WORKER_TRANSITIONS,
    require_attempt_transition,
    require_run_transition,
    require_task_transition,
    require_worker_transition,
)

# --- Every legal edge in each table succeeds -------------------------------------


@pytest.mark.parametrize(
    ("current", "target"),
    [(c, t) for c, targets in RUN_TRANSITIONS.items() for t in targets],
)
def test_every_legal_run_transition_succeeds(current: RunState, target: RunState) -> None:
    require_run_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [(c, t) for c, targets in TASK_TRANSITIONS.items() for t in targets],
)
def test_every_legal_task_transition_succeeds(current: TaskState, target: TaskState) -> None:
    require_task_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [(c, t) for c, targets in WORKER_TRANSITIONS.items() for t in targets],
)
def test_every_legal_worker_transition_succeeds(current: WorkerState, target: WorkerState) -> None:
    require_worker_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [(c, t) for c, targets in ATTEMPT_TRANSITIONS.items() for t in targets],
)
def test_every_legal_attempt_transition_succeeds(
    current: AttemptState, target: AttemptState
) -> None:
    require_attempt_transition(current, target)


# --- Representative illegal edges are rejected ------------------------------------


def test_pending_task_cannot_jump_to_committed() -> None:
    with pytest.raises(IllegalTransitionError):
        require_task_transition(TaskState.PENDING, TaskState.COMMITTED)


def test_planning_run_cannot_jump_to_merging() -> None:
    with pytest.raises(IllegalTransitionError):
        require_run_transition(RunState.PLANNING, RunState.MERGING)


def test_idle_worker_cannot_jump_to_busy() -> None:
    with pytest.raises(IllegalTransitionError):
        require_worker_transition(WorkerState.IDLE, WorkerState.BUSY)


def test_assigned_attempt_cannot_jump_to_staged() -> None:
    with pytest.raises(IllegalTransitionError):
        require_attempt_transition(AttemptState.ASSIGNED, AttemptState.STAGED)


# --- Terminal states have zero legal successors (INV-017) -------------------------


@pytest.mark.parametrize("terminal", [TaskState.COMMITTED, TaskState.FAILED, TaskState.CANCELLED])
def test_terminal_task_states_reject_every_other_target(terminal: TaskState) -> None:
    for target in TaskState:
        if target is terminal:
            continue
        with pytest.raises(IllegalTransitionError):
            require_task_transition(terminal, target)


# --- §28 Table 15 "commit wins" cancellation race ----------------------------------


def test_committed_task_cannot_be_retroactively_cancelled() -> None:
    """§28 Table 15: 'Cancel races with commit transaction' — if commit lands first,
    run cancellation must not rewrite the committed task. COMMITTED's empty
    transition set (TASK_TRANSITIONS) is what enforces this."""
    with pytest.raises(IllegalTransitionError):
        require_task_transition(TaskState.COMMITTED, TaskState.CANCELLED)


def test_staged_task_can_still_be_cancelled_before_commit() -> None:
    """§28 Table 15: 'Cancel after staging but before commit' is legal — the staged
    artifact simply never gets committed."""
    require_task_transition(TaskState.STAGED, TaskState.CANCELLED)


# --- Idempotent self-transitions ---------------------------------------------------


def test_idempotent_self_transition_allowed_by_default() -> None:
    require_task_transition(TaskState.RUNNING, TaskState.RUNNING)


def test_idempotent_self_transition_rejected_when_disabled() -> None:
    with pytest.raises(IllegalTransitionError):
        require_task_transition(TaskState.RUNNING, TaskState.RUNNING, allow_idempotent=False)


def test_terminal_state_self_transition_still_requires_allow_idempotent() -> None:
    # COMMITTED -> COMMITTED has no entry in TASK_TRANSITIONS[COMMITTED]; only the
    # allow_idempotent short-circuit makes it legal.
    require_task_transition(TaskState.COMMITTED, TaskState.COMMITTED)
    with pytest.raises(IllegalTransitionError):
        require_task_transition(TaskState.COMMITTED, TaskState.COMMITTED, allow_idempotent=False)
