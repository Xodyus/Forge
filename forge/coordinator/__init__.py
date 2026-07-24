"""forge.coordinator — Submission, worker registry, scheduling, leases, commits,
cancellation, recovery.

Responsibility: the single logical leader that owns run and task state.
Boundary: single logical leader; depends on forge.metadata and forge.artifacts through
their interfaces, not concrete SQLite paths or directory layouts (§38, §40,
docs/spec/part-03-architecture.md).
"""
