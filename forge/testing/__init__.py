"""forge.testing — Fakes, deterministic clock, fault injector, model oracles.

Responsibility: test-only control surfaces used by tests/ and forge.bench.
Boundary: test-only; core packages must not import forge.testing outside of test
contexts (§38, §40, docs/spec/part-03-architecture.md).
"""
