"""State enums for the run, task, attempt, and worker life cycles.

``RunState``, ``TaskState``, and ``WorkerState`` are transcribed directly from Part II
of the spec (§29 Table 16, §21 Table 12, §30 Table 17 respectively) — every member
name and its allowed successors in :mod:`forge.domain.transitions` trace back to
those tables.

``AttemptState`` has no equivalent explicit table in Part II. It is synthesized here
from Appendix B §353's skeleton enum (``ASSIGNED, RUNNING, STAGED, COMMITTED, FAILED,
EXPIRED, CANCELLED, REJECTED_STALE``) plus the lease, retry, and commit prose in
§21–§23 and §27. Treat this enum — and the transition table built on it — as a
documented design decision, not a spec quotation; revisit it if a later week's
coordinator work surfaces a state Part II's prose didn't anticipate.
"""

from __future__ import annotations

from enum import StrEnum


class RunState(StrEnum):
    """Run lifecycle (§29 Table 16)."""

    SUBMITTED = "submitted"
    PLANNING = "planning"
    RUNNING = "running"
    MERGING = "merging"
    CANCELLING = "cancelling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TaskState(StrEnum):
    """Logical task lifecycle (§21 Table 12)."""

    PENDING = "pending"
    LEASED = "leased"
    RUNNING = "running"
    STAGED = "staged"
    COMMITTED = "committed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerState(StrEnum):
    """Worker lifecycle (§30 Table 17)."""

    REGISTERING = "registering"
    IDLE = "idle"
    LEASED = "leased"
    BUSY = "busy"
    DRAINING = "draining"
    LOST = "lost"
    QUARANTINED = "quarantined"


class AttemptState(StrEnum):
    """Physical attempt lifecycle. See module docstring: synthesized, not tabulated
    verbatim in Part II."""

    ASSIGNED = "assigned"
    RUNNING = "running"
    STAGED = "staged"
    COMMITTED = "committed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REJECTED_STALE = "rejected_stale"


TERMINAL_RUN_STATES: frozenset[RunState] = frozenset(
    {RunState.SUCCEEDED, RunState.FAILED, RunState.CANCELLED, RunState.REJECTED}
)

TERMINAL_TASK_STATES: frozenset[TaskState] = frozenset(
    {TaskState.COMMITTED, TaskState.FAILED, TaskState.CANCELLED}
)

TERMINAL_ATTEMPT_STATES: frozenset[AttemptState] = frozenset(
    {
        AttemptState.COMMITTED,
        AttemptState.FAILED,
        AttemptState.EXPIRED,
        AttemptState.CANCELLED,
        AttemptState.REJECTED_STALE,
    }
)
