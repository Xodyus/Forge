"""forge.observability — Logging context, metrics, traces, diagnostic bundle.

Responsibility: structured logs, metrics, traces, status views, and diagnostic
bundles.
Boundary: never authoritative for state; must not be a required dependency for
correctness decisions made in forge.coordinator or forge.domain (§38,
docs/spec/part-03-architecture.md).
"""
