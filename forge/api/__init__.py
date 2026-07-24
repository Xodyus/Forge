"""forge.api — Public Python models and user-facing client objects.

Responsibility: run manifests, IDs, immutable status views.
Boundary: exposes the public surface consumed by forge.cli and external callers; must
not contain coordinator, metadata, or transport implementation details (§38, §40,
docs/spec/part-03-architecture.md).
"""
