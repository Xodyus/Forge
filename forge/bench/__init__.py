"""forge.bench — Workload manifests, runner, raw record schema, analysis.

Responsibility: benchmark workload definitions, trial execution, and raw-evidence
analysis.
Boundary: separate from the production-like execution path; core packages
(forge.domain, forge.planner, forge.coordinator, forge.metadata, forge.artifacts,
forge.protocol, forge.transport, forge.worker, forge.kernels, forge.datasets,
forge.api, forge.cli, forge.observability) must not import forge.bench (§38, §40,
docs/spec/part-03-architecture.md).
"""
