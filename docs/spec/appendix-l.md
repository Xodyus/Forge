# Appendix L - Review Checklists, Glossary, and Final Acceptance

## 423. Pull Request Checklist

- The PR names the requirement, invariant, state transition, or benchmark question it changes.
- The happy path and at least the relevant duplicate, retry, cancellation, or restart path are tested.
- Transaction boundaries are visible and do not include uncontrolled I/O or network calls.
- Any new queue, buffer, frame, file, process, timer, cache, or log is bounded and has one cleanup owner.
- Errors are typed, classified, and observable; broad exception swallowing is absent.
- Identifiers and fencing epochs are validated at trust boundaries.
- Paths are resolved under approved roots and symlink/traversal behavior is tested.
- Protocol or schema changes include fixtures, version behavior, and compatibility documentation.
- Native code includes ownership/GIL reasoning and sanitizer/differential tests.
- Performance-sensitive changes include a profile or before/after evidence when warranted.
- Documentation, diagrams, ADRs, and claim map are updated when public behavior changes.
- The change is reproducible in a clean environment and does not rely on personal state.

## 424. Architecture Review Checklist

- Can the reviewer state the system guarantee in one precise sentence?
- Are logical task identity and physical attempt identity separate everywhere?
- Is durable truth clearly separated from connection/session/in-memory state?
- Can every retry or duplicate message be processed idempotently or rejected safely?
- Does every state transition have one owner and one transaction/event boundary?
- Can stale actors be fenced from mutable or visible resources?
- Are control and large data paths separated?
- Are all resource queues and caches bounded with overload behavior?
- Is coordinator restart based only on durable evidence?
- Does cancellation have a documented barrier and race ordering?
- Does the design state trust, security, platform, storage, and single-leader limits?
- Can the simple reference path remain operational while optimized paths evolve?

## 425. Performance Review Checklist

- Is the question defined before measurement?
- Are source, input, configuration, and environment identities frozen?
- Are correctness digests checked for every trial?
- Are timing boundaries and warm-up/cache policies explicit?
- Are raw trials retained and failed trials classified?
- Are whole-system and component costs both available?
- Are worker-count results accompanied by speedup and efficiency?
- Are memory and CPU costs reported with throughput improvements?
- Is the claimed cause supported by profile or controlled intervention?
- Are neutral/negative results and limitations preserved?
- Can plots be regenerated from raw evidence without manual editing?
- Does public wording remain specific to the measured workload and host?

## 426. Security Review Checklist

- Is arbitrary pickle or object deserialization excluded from network and persisted trust boundaries?
- Are frame sizes, message counts, strings, status pages, logs, queues, tasks, and artifact bytes bounded?
- Are all file paths relative, rooted, normalized, and protected against traversal and symlink attacks?
- Does local binding and filesystem permission form the default exposure?
- Are multi-host authentication and encryption explicit rather than implied?
- Are kernels clearly trusted and not described as sandboxed?
- Are secrets absent from manifests, logs, bundles, fixtures, and release history?
- Are temporary files created exclusively and published atomically?
- Can a malicious manifest cause overflow, huge allocation, or excessive task creation before admission checks?
- Are dependencies minimal, pinned for evidence, scanned, and licensed?
- Does diagnostic collection redact or bound sensitive fields?
- Are security limitations stated in the README and threat-model document?

## 427. Glossary

**Table 146 --- Forge glossary.**

  -------------------------------------------------------------------------------------------------------------------------------------------
  Term                           Definition
  ------------------------------ ------------------------------------------------------------------------------------------------------------
  admission control              Policy that limits which runs or tasks may consume resources before scheduling.

  artifact                       Immutable file or object produced by one attempt or final merge, identified by descriptor and digest.

  attempt                        One physical execution of a logical task. A task may have multiple attempts over time.

  backpressure                   Mechanism that slows or rejects producers when bounded downstream capacity is exhausted.

  canonical result               Normalized logical output whose digest is independent of worker count, attempt IDs, timestamps, and paths.

  checkpoint                     Durable manifest describing a recoverable frontier or merge state; not automatically a full backup.

  commit                         Conditional durable selection of one attempt artifact as the visible task result.

  control plane                  Small messages and durable decisions for registration, scheduling, leases, status, and commits.

  data plane                     Movement or reading of dataset and result bytes, normally through immutable files in Forge.

  dataset                        Immutable, versioned collection of event files and a manifest with content identity.

  determinism                    Equal frozen inputs and supported software semantics produce equal canonical output.

  diagnostic bundle              Bounded, redacted collection of state, logs, manifests, versions, and artifacts for investigation.

  exactly-once visible commit    At most one result becomes authoritative per task even though physical attempts may duplicate.

  fencing epoch                  Monotonic authorization value used to reject operations from stale lease holders.

  fault point                    Named deterministic location where a test may delay, fail, corrupt, or terminate a component.

  kernel                         Registered trusted computation that consumes event batches and produces a versioned partial result.

  lease                          Time-bounded authorization for a worker attempt to execute and seek commit.

  manifest                       Canonical versioned metadata document describing data, experiment, run, artifact, benchmark, or evidence.

  partition                      Deterministic immutable range of dataset records assigned to one logical task.

  publication                    Making a validated artifact visible through the final path or authoritative result association.

  reconciliation                 Startup or maintenance process that compares durable metadata and files and classifies discrepancies.

  reference engine               Deliberately simple sequential implementation used as a correctness oracle.

  run                            Durable execution of one validated experiment manifest over one immutable dataset identity.

  session                        Ephemeral network connection identity distinct from a durable worker identity.

  staging                        Attempt-specific creation of output before task-level commit and visibility.

  task                           Logical deterministic computation for one partition and kernel configuration.

  worker                         Service that polls for leases and supervises isolated attempt processes.

  workload manifest              Frozen description of benchmark input, parameters, environment controls, and trial policy.
  -------------------------------------------------------------------------------------------------------------------------------------------

## 428. Final Gate F Acceptance Checklist

**Table 147 --- Gate F final acceptance checklist.**

  -------------------------------------------------------------------------------------------------------------------------------------
  Area                           Acceptance condition
  ------------------------------ ------------------------------------------------------------------------------------------------------
  Semantics                      All public guarantees, state transitions, retries, cancellation, and non-goals match code and tests.

  Reference                      Sequential engine and canonical outputs are reproducible from immutable fixtures.

  Durability                     Coordinator restart and artifact reconciliation pass documented crash points.

  Commit                         Duplicate attempts and both commit race orders preserve one visible result.

  Workers                        Process lifecycle, cancellation, timeout, logging, resource bounds, and cleanup pass soak tests.

  Protocol                       Framing, chunking, partial writes, versioning, limits, reconnect, and fuzz tests pass.

  Native                         C++ extension is optional, sanitizer-clean in tested config, differential, packaged, and measured.

  Observability                  Status, logs, metrics, timelines, and diagnostics reconstruct important transitions.

  Security                       Trusted boundary and safe local defaults are explicit; path and deserialization tests pass.

  Benchmark                      Raw trials, environment, manifests, analysis, correctness digests, and claim review are complete.

  Documentation                  README, technical docs, diagrams, ADRs, postmortem, examples, and operations agree.

  Release                        Clean artifact install, demos, evidence regeneration, checksums, license, and changelog pass.

  Portfolio                      Claim map, resume wording, code tour, demo, and interview stories contain no unsupported statement.
  -------------------------------------------------------------------------------------------------------------------------------------
