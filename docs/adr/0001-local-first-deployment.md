# ADR-0001: Local-first deployment

Status: Proposed

## Context

§35 (Architectural Priorities) states that correctness and inspectability outrank
peak throughput in the first implementation, and that optional complexity must be
replaceable behind an interface: "A Unix-domain socket may become TCP; a file path
may become an object key; the task semantics remain stable."

§36 (System Context) states the baseline directly: "The baseline is local-first: all
processes run on one Linux host and share a filesystem. This creates enough realism
to demonstrate process boundaries, sockets, leases, crashes, durable state, and
backpressure without requiring cloud infrastructure. A later multi-host mode is an
adapter and deployment exercise, not a rewrite of semantics."

§37 (Deployment Modes) enumerates six modes on a spectrum from a single reference
process to a trusted multi-host TCP deployment and a shared-memory experiment, and
states that "every mode must use the same accepted run manifest, partition plan, task
identifiers, kernel registry, result schema, and canonical digest. Deployment changes
may affect timing and attempt history, not logical output."

§267 (Planning Constraints) adds a resource-limits constraint: "The default demo must
run on a typical laptop with bounded disk and memory. Reviewers should not need cloud
infrastructure," and a scope-control constraint: "Optional distributed features need
a measured bottleneck or explicit learning hypothesis. Novelty alone is not sufficient
justification."

§13 (Scope-Control Rules) is explicit that "No multi-host mode [is allowed] before
restart recovery is reliable on one host," and §4 (Explicit Non-Goals) rules out
"dynamic cluster autoscaling, cloud billing integration, heterogeneous accelerator
scheduling, or fleet management" and "cross-region disaster recovery" for the first
public release.

The question this ADR must settle: what is the deployment topology for the reference
and Gate A/B implementations, and what must every later deployment mode preserve so
that adding sockets, TCP, or multi-host execution is an adapter change rather than a
semantics rewrite?

## Alternatives to consider

- **Local-first, single-host, filesystem-shared** (§36 baseline): one Python
  reference process initially, then a coordinator plus multiprocessing children
  (Embedded local, Gate A), then coordinator and independent worker processes over a
  Unix-domain socket or loopback TCP on the same host (Socket local / Loopback TCP,
  Gate B), sharing one filesystem for datasets, artifacts, and metadata.
- **Multi-host first**: design the coordinator/worker protocol and metadata store for
  network partition tolerance and a distributed filesystem or object store from day
  one. Ruled out by §13 ("No multi-host mode before restart recovery is reliable on
  one host") and §4 (no cloud billing integration, no cross-region disaster
  recovery) unless a later experiment explicitly isolates it (§37's "Trusted
  multi-host" row is marked priority P2, not MVP or Gate A/B).
- **Container/orchestrator-first** (e.g., assume Kubernetes or Docker Compose as the
  only supported environment): ruled out by §260 ("Provide a development container
  ... for toolchain convenience, not as the only supported environment") and by the
  laptop resource-limit constraint in §267.
- **Cloud-managed services from the start** (managed queue, managed database instead
  of SQLite, managed object storage instead of local files): ruled out by §4's
  non-goals (no cloud billing integration) and by §257's dependency policy ("Avoid
  adding a full distributed framework that hides the mechanisms Forge is intended to
  demonstrate").

## Decision

TODO (project owner).

## Consequences

TODO (project owner).
