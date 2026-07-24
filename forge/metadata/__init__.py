"""forge.metadata — Transactional persistence interface and SQLite implementation.

Responsibility: durable coordination truth for runs, tasks, attempts, leases, and
commits.
Boundary: owned exclusively by forge.coordinator; must not be imported by
forge.domain or forge.planner (§38, §40, docs/spec/part-03-architecture.md).
"""
