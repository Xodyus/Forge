"""forge.worker — Worker process, task runtime, kernel dispatch, staging, telemetry.

Responsibility: pull leased tasks, execute registered kernels, and produce
attempt-scoped staged output.
Boundary: no durable commit authority; depends on forge.protocol and forge.kernels
interfaces but must not import forge.coordinator internals (§38, §40,
docs/spec/part-03-architecture.md).
"""
