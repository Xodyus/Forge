"""forge.artifacts — Immutable artifact writer, verifier, publisher, and cleanup
policy.

Responsibility: bytes and digests; no scheduling decisions.
Boundary: promotion and cleanup are conditional on durable task state supplied by
forge.coordinator; this package does not decide leases or commits itself (§38, §40,
docs/spec/part-03-architecture.md).
"""
