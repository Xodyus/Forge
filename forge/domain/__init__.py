"""forge.domain — Enums, value objects, state transitions, validation, invariants.

Responsibility: the pure execution vocabulary (dataset, run, task, attempt, lease,
worker, artifact, checkpoint, commit) and the state machines that govern it.
Boundary: no sockets, database handles, or filesystem I/O. Must not import
forge.coordinator, forge.metadata, forge.artifacts, forge.protocol, forge.transport,
forge.worker, forge.cli, forge.api, or forge.bench (§38, §40, §41,
docs/spec/part-03-architecture.md).
"""
