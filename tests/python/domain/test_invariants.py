import pytest
from forge.domain.invariants import (
    InvariantViolationError,
    assert_at_most_one_committed_attempt,
    assert_attempt_belongs_to_one_task_and_generation,
    assert_committed_path_not_reused,
    assert_committed_task_has_matching_artifact,
    assert_fencing_generations_increase,
    assert_generation_not_stale,
    assert_no_transition_from_terminal_task_state,
    assert_retry_count_consistent,
    assert_schema_version_supported,
    assert_staging_paths_unique,
)
from forge.domain.states import AttemptState, TaskState

# INV-001


def test_inv001_allows_zero_or_one_committed_attempt() -> None:
    assert_at_most_one_committed_attempt([AttemptState.FAILED, AttemptState.COMMITTED])


def test_inv001_rejects_two_committed_attempts() -> None:
    with pytest.raises(InvariantViolationError, match="INV-001"):
        assert_at_most_one_committed_attempt([AttemptState.COMMITTED, AttemptState.COMMITTED])


# INV-002


def test_inv002_committed_task_needs_attempt_and_digest() -> None:
    with pytest.raises(InvariantViolationError, match="INV-002"):
        assert_committed_task_has_matching_artifact(TaskState.COMMITTED, None, "digest")


def test_inv002_non_committed_task_has_no_requirement() -> None:
    assert_committed_task_has_matching_artifact(TaskState.PENDING, None, None)


def test_inv002_committed_task_with_both_fields_passes() -> None:
    assert_committed_task_has_matching_artifact(TaskState.COMMITTED, "attempt-1", "digest")


# INV-004


def test_inv004_rejects_wrong_task_id() -> None:
    with pytest.raises(InvariantViolationError, match="INV-004"):
        assert_attempt_belongs_to_one_task_and_generation("task-a", "task-b", 1, 1)


def test_inv004_rejects_wrong_generation() -> None:
    with pytest.raises(InvariantViolationError, match="INV-004"):
        assert_attempt_belongs_to_one_task_and_generation("task-a", "task-a", 1, 2)


def test_inv004_passes_when_matched() -> None:
    assert_attempt_belongs_to_one_task_and_generation("task-a", "task-a", 3, 3)


# INV-005


def test_inv005_rejects_non_increasing_epoch() -> None:
    with pytest.raises(InvariantViolationError, match="INV-005"):
        assert_fencing_generations_increase(previous_epoch=2, next_epoch=2)


def test_inv005_rejects_decreasing_epoch() -> None:
    with pytest.raises(InvariantViolationError, match="INV-005"):
        assert_fencing_generations_increase(previous_epoch=3, next_epoch=1)


def test_inv005_passes_when_increasing() -> None:
    assert_fencing_generations_increase(previous_epoch=1, next_epoch=2)


# INV-006


def test_inv006_rejects_stale_generation() -> None:
    with pytest.raises(InvariantViolationError, match="INV-006"):
        assert_generation_not_stale(attempt_epoch=1, current_epoch=2, action="commit")


def test_inv006_passes_for_current_generation() -> None:
    assert_generation_not_stale(attempt_epoch=2, current_epoch=2, action="commit")


# INV-009


def test_inv009_rejects_content_change_at_same_path() -> None:
    with pytest.raises(InvariantViolationError, match="INV-009"):
        assert_committed_path_not_reused("artifacts/task-1", "digest-a", "digest-b")


def test_inv009_passes_for_identical_content() -> None:
    assert_committed_path_not_reused("artifacts/task-1", "digest-a", "digest-a")


# INV-010


def test_inv010_rejects_duplicate_staging_path() -> None:
    with pytest.raises(InvariantViolationError, match="INV-010"):
        assert_staging_paths_unique(["staging/a", "staging/b", "staging/a"])


def test_inv010_passes_for_unique_paths() -> None:
    assert_staging_paths_unique(["staging/a", "staging/b"])


# INV-012


def test_inv012_rejects_mismatched_retry_count() -> None:
    with pytest.raises(InvariantViolationError, match="INV-012"):
        assert_retry_count_consistent(attempt_count=3, retry_count=1)


def test_inv012_rejects_zero_attempts() -> None:
    with pytest.raises(InvariantViolationError, match="INV-012"):
        assert_retry_count_consistent(attempt_count=0, retry_count=0)


def test_inv012_passes_when_consistent() -> None:
    assert_retry_count_consistent(attempt_count=3, retry_count=2)


# INV-017


def test_inv017_rejects_leaving_committed() -> None:
    with pytest.raises(InvariantViolationError, match="INV-017"):
        assert_no_transition_from_terminal_task_state(TaskState.COMMITTED, TaskState.PENDING)


def test_inv017_allows_non_terminal_movement() -> None:
    assert_no_transition_from_terminal_task_state(TaskState.PENDING, TaskState.LEASED)


def test_inv017_allows_terminal_self_transition() -> None:
    assert_no_transition_from_terminal_task_state(TaskState.FAILED, TaskState.FAILED)


# INV-020


def test_inv020_rejects_unsupported_schema_version() -> None:
    with pytest.raises(InvariantViolationError, match="INV-020"):
        assert_schema_version_supported(2, [1], schema_name="forge.run")


def test_inv020_passes_for_supported_version() -> None:
    assert_schema_version_supported(1, [1], schema_name="forge.run")
