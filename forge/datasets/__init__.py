"""forge.datasets — Synthetic generator, manifest tools, readers, partition index.

Responsibility: immutable inputs consumed by forge.planner and forge.worker.
Boundary: produces and reads immutable dataset files; does not decide partitioning
policy itself (§38, docs/spec/part-03-architecture.md).
"""
