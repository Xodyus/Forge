"""forge.planner — Dataset validation and deterministic partition/task planning.

Responsibility: turn a validated dataset and experiment manifest into an immutable,
deterministic partition and task plan.
Boundary: pure or explicitly parameterized. Must not import forge.coordinator,
forge.metadata, forge.artifacts, forge.protocol, forge.transport, forge.worker,
forge.cli, forge.api, or forge.bench (§38, §40, §41,
docs/spec/part-03-architecture.md).
"""
