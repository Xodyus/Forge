"""Pure assertion helpers for the invariants checkable from domain objects alone
(§31 Table 18).

Ten of the twenty invariants need durable metadata, live queues, or a running
coordinator to mean anything (INV-003, 007, 008, 011, 013, 014, 015, 016, 018, 019).
Those are catalogued with their planned test location in
``docs/semantics/invariants.md`` rather than stubbed here — an assertion function
that cannot observe the state it is supposed to check would be a false promise, not
a test. This module implements the other ten, each directly callable against
:mod:`forge.domain.descriptors` and :mod:`forge.domain.states` objects.
"""

from __future__ import annotations

from collections.abc import Sequence

from forge.domain.states import AttemptState, TaskState


class InvariantViolationError(AssertionError):
    """Raised when a checked invariant does not hold."""


def assert_at_most_one_committed_attempt(
    attempt_states: Sequence[AttemptState],
) -> None:
    """INV-001: At most one committed attempt exists for a task."""
    committed = sum(1 for state in attempt_states if state is AttemptState.COMMITTED)
    if committed > 1:
        raise InvariantViolationError(
            f"INV-001: expected at most one COMMITTED attempt, found {committed}"
        )


def assert_committed_task_has_matching_artifact(
    task_state: TaskState,
    committed_attempt_id: object | None,
    committed_digest: object | None,
) -> None:
    """INV-002: A committed task has a committed artifact reference and matching
    digest."""
    if task_state is TaskState.COMMITTED and (
        committed_attempt_id is None or committed_digest is None
    ):
        raise InvariantViolationError(
            "INV-002: COMMITTED task must carry a committed attempt id and digest"
        )


def assert_attempt_belongs_to_one_task_and_generation(
    attempt_task_id: object,
    expected_task_id: object,
    attempt_fencing_epoch: int,
    expected_fencing_epoch: int,
) -> None:
    """INV-004: A task attempt belongs to exactly one task and one worker lease
    generation."""
    if attempt_task_id != expected_task_id:
        raise InvariantViolationError("INV-004: attempt does not belong to the expected task")
    if attempt_fencing_epoch != expected_fencing_epoch:
        raise InvariantViolationError(
            "INV-004: attempt does not belong to the expected lease generation"
        )


def assert_fencing_generations_increase(previous_epoch: int, next_epoch: int) -> None:
    """INV-005: Fencing generations for a task increase monotonically."""
    if next_epoch <= previous_epoch:
        raise InvariantViolationError(
            f"INV-005: fencing epoch must increase, got {previous_epoch} -> {next_epoch}"
        )


def assert_generation_not_stale(
    attempt_epoch: int,
    current_epoch: int,
    *,
    action: str,
) -> None:
    """INV-006: A stale generation cannot renew a lease or become committed."""
    if attempt_epoch < current_epoch:
        raise InvariantViolationError(
            f"INV-006: stale generation {attempt_epoch} < {current_epoch} attempted {action}"
        )


def assert_committed_path_not_reused(
    path: object,
    existing_digest: object,
    new_digest: object,
) -> None:
    """INV-009: Committed artifact paths are immutable and never reused for
    different content."""
    if existing_digest != new_digest:
        raise InvariantViolationError(
            f"INV-009: committed path {path!r} already holds different content"
        )


def assert_staging_paths_unique(paths: Sequence[object]) -> None:
    """INV-010: Attempt staging paths are unique and cannot overwrite another
    attempt."""
    seen: set[object] = set()
    for path in paths:
        if path in seen:
            raise InvariantViolationError(f"INV-010: duplicate attempt staging path {path!r}")
        seen.add(path)


def assert_retry_count_consistent(attempt_count: int, retry_count: int) -> None:
    """INV-012: Retry count equals the number of created attempts minus the initial
    attempt, subject to explicit administrative operations."""
    if attempt_count < 1:
        raise InvariantViolationError(
            "INV-012: a task must have at least one attempt to have a retry count"
        )
    expected = attempt_count - 1
    if retry_count != expected:
        raise InvariantViolationError(
            f"INV-012: expected retry_count={expected} for {attempt_count} attempts, "
            f"got {retry_count}"
        )


def assert_no_transition_from_terminal_task_state(
    from_state: TaskState,
    to_state: TaskState,
) -> None:
    """INV-017: A task cannot transition from COMMITTED, FAILED, or CANCELLED back
    to an executable state.

    This duplicates part of what :func:`forge.domain.transitions.require_task_transition`
    already enforces structurally (terminal states have empty transition sets); it is
    kept here too because INV-017 is explicitly named in §31 and callers that only
    have two state values on hand — not the full transition table — should still be
    able to check it directly.
    """
    terminal_task_states = {TaskState.COMMITTED, TaskState.FAILED, TaskState.CANCELLED}
    if from_state in terminal_task_states and to_state is not from_state:
        raise InvariantViolationError(f"INV-017: cannot leave terminal task state {from_state}")


def assert_schema_version_supported(
    schema_version: int,
    supported_versions: Sequence[int],
    *,
    schema_name: str,
) -> None:
    """INV-020: All schema and protocol versions are validated before their fields
    are interpreted."""
    if schema_version not in supported_versions:
        raise InvariantViolationError(
            f"INV-020: unsupported {schema_name} schema_version {schema_version}; "
            f"supported: {sorted(supported_versions)}"
        )
