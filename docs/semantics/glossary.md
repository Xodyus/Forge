# Glossary

Extracted verbatim from [docs/spec/appendix-l.md §427](../spec/appendix-l.md). This is
the canonical vocabulary (§15) every other document and every identifier in the
codebase should agree with. If this file and appendix-l.md ever disagree,
appendix-l.md is authoritative — update this file to match, not the other way around.

| Term | Definition |
|---|---|
| admission control | Policy that limits which runs or tasks may consume resources before scheduling. |
| artifact | Immutable file or object produced by one attempt or final merge, identified by descriptor and digest. |
| attempt | One physical execution of a logical task. A task may have multiple attempts over time. |
| backpressure | Mechanism that slows or rejects producers when bounded downstream capacity is exhausted. |
| canonical result | Normalized logical output whose digest is independent of worker count, attempt IDs, timestamps, and paths. |
| checkpoint | Durable manifest describing a recoverable frontier or merge state; not automatically a full backup. |
| commit | Conditional durable selection of one attempt artifact as the visible task result. |
| control plane | Small messages and durable decisions for registration, scheduling, leases, status, and commits. |
| data plane | Movement or reading of dataset and result bytes, normally through immutable files in Forge. |
| dataset | Immutable, versioned collection of event files and a manifest with content identity. |
| determinism | Equal frozen inputs and supported software semantics produce equal canonical output. |
| diagnostic bundle | Bounded, redacted collection of state, logs, manifests, versions, and artifacts for investigation. |
| exactly-once visible commit | At most one result becomes authoritative per task even though physical attempts may duplicate. |
| fencing epoch | Monotonic authorization value used to reject operations from stale lease holders. |
| fault point | Named deterministic location where a test may delay, fail, corrupt, or terminate a component. |
| kernel | Registered trusted computation that consumes event batches and produces a versioned partial result. |
| lease | Time-bounded authorization for a worker attempt to execute and seek commit. |
| manifest | Canonical versioned metadata document describing data, experiment, run, artifact, benchmark, or evidence. |
| partition | Deterministic immutable range of dataset records assigned to one logical task. |
| publication | Making a validated artifact visible through the final path or authoritative result association. |
| reconciliation | Startup or maintenance process that compares durable metadata and files and classifies discrepancies. |
| reference engine | Deliberately simple sequential implementation used as a correctness oracle. |
| run | Durable execution of one validated experiment manifest over one immutable dataset identity. |
| session | Ephemeral network connection identity distinct from a durable worker identity. |
| staging | Attempt-specific creation of output before task-level commit and visibility. |
| task | Logical deterministic computation for one partition and kernel configuration. |
| worker | Service that polls for leases and supervises isolated attempt processes. |
| workload manifest | Frozen description of benchmark input, parameters, environment controls, and trial policy. |
