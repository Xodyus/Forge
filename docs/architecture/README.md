# Architecture

Stub. This document will hold the architecture.md content required by §261
(components, flows, deployment modes, ownership, decisions) once the components it
describes exist. Until then, treat docs/spec/part-03-architecture.md as authoritative
and read it in full before implementing any component (see docs/spec/INDEX.md).

## Diagrams to produce (§36–§45)

Two figures already exist in the specification and can be reused or adapted directly:

- Figure 3 — system context and primary components (§36,
  `docs/spec/media/rId73.png`).
- Figure 4 — control-plane messages separated from large data movement (§39,
  `docs/spec/media/rId79.png`).

The rest are not illustrated in the spec yet and are TODO here:

- [ ] §37 Deployment modes — a comparison diagram of the six modes (Reference,
      Embedded local, Socket local, Loopback TCP, Trusted multi-host,
      Shared-memory experiment): processes, transport, storage assumption, and gate
      for each.
- [ ] §38 Component inventory — a box diagram of the fifteen `forge.*` packages plus
      `forge_cpp`, matching the table already in CLAUDE.md.
- [ ] §40 Dependency direction — a formal version of the ASCII dependency graph in
      CLAUDE.md (`forge.api/forge.cli` → `forge.coordinator` → `forge.domain` ←
      `forge.worker`, etc.).
- [ ] §42 Process and threading model — which components are processes, which are
      threads or async tasks within a process, and where the process boundary sits
      between coordinator and worker.
- [ ] §43 End-to-end command and data flow — a sequence diagram from client
      submission through partitioning, leasing, execution, staging, and commit.
- [ ] §44 Bounded queues and backpressure — where every bounded queue in the system
      lives and what happens when it is full.
- [ ] §45 Ownership map — which component owns which durable state, files, and
      processes, and who is allowed to mutate what.

Do not draw these from memory. Each diagram should be checked against its section in
[docs/spec/part-03-architecture.md](../spec/part-03-architecture.md) once the
corresponding component is implemented, not before.
