"""forge.cli — Command-line interface and scripted demonstration.

Responsibility: text/JSON output; no hidden business logic.
Boundary: calls forge.api only; must not implement coordinator, worker, or storage
logic directly (§38, §40, docs/spec/part-03-architecture.md).
"""
