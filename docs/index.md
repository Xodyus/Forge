# Forge

A deterministic, local-first event-replay and compute engine written primarily in
Python, with a modern C++20 extension for performance-critical parsing and
aggregation. See the repository [README](https://github.com/Xodyus/Forge) for the
full project thesis, build instructions, and gate status.

This site is a documentation skeleton (§261 required documentation set). Most of it
will fill in gate by gate, alongside the code — it is not meant to get ahead of what's
actually implemented.

## Start here

- [Specification index](spec/INDEX.md) — section-range → file lookup for the full
  434-section master build spec. Read the relevant Part before implementing anything
  against it.
- [Architecture](architecture/README.md) — component map and diagram TODOs (currently
  a stub; see docs/spec/part-03-architecture.md for the authoritative source).
- [Glossary](semantics/glossary.md) — the canonical execution vocabulary (§427).
- [Architecture decision records](adr/0000-template.md) — durable record of
  project-owner judgment calls, one file per decision.

## Not written yet

`protocol.md`, `storage.md`, `testing.md`, `benchmarks.md`, `operations.md`, and
`security.md` (§261) don't exist as standalone docs yet — read the corresponding
`docs/spec/part-*.md` file instead until each component is built and its usage docs
are written from the real implementation, not from the spec alone.
