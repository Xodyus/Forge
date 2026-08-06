from forge.domain.states import (
    TERMINAL_ATTEMPT_STATES,
    TERMINAL_RUN_STATES,
    TERMINAL_TASK_STATES,
    AttemptState,
    RunState,
    TaskState,
    WorkerState,
)


def test_run_state_has_nine_members_per_table_16() -> None:
    assert len(RunState) == 9


def test_task_state_has_seven_members_per_table_12() -> None:
    assert len(TaskState) == 7


def test_worker_state_has_seven_members_per_table_17() -> None:
    assert len(WorkerState) == 7


def test_terminal_run_states_match_table_16() -> None:
    assert {
        RunState.SUCCEEDED,
        RunState.FAILED,
        RunState.CANCELLED,
        RunState.REJECTED,
    } == TERMINAL_RUN_STATES


def test_terminal_task_states_match_table_12() -> None:
    assert {TaskState.COMMITTED, TaskState.FAILED, TaskState.CANCELLED} == TERMINAL_TASK_STATES


def test_terminal_attempt_states_exclude_active_states() -> None:
    assert AttemptState.ASSIGNED not in TERMINAL_ATTEMPT_STATES
    assert AttemptState.RUNNING not in TERMINAL_ATTEMPT_STATES
    assert AttemptState.STAGED not in TERMINAL_ATTEMPT_STATES
    assert AttemptState.COMMITTED in TERMINAL_ATTEMPT_STATES
