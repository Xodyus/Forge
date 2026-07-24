# Appendix A - Requirements Traceability Matrix

## 350. How to Maintain Traceability

Requirements traceability prevents the public narrative from drifting away from the implemented system. Each requirement should have one owning module, one primary acceptance layer, one release gate, and one evidence location. A requirement may have many tests, but the matrix should point to the smallest test or scenario that demonstrates the defining behavior. Update this appendix or its repository equivalent whenever a requirement changes state, wording, priority, or scope.

**Table 129 --- Functional-requirement traceability.**

  -----------------------------------------------------------------------------------------------------------------------
  Requirement     Owning component                          Primary evidence                            Target gate
  --------------- ----------------------------------------- ------------------------------------------- -----------------
  FR-001          manifest models; dataset registry         schema/golden/integrity tests               Gate A

  FR-002          submission service; runs repository       idempotent submission integration           Gate B

  FR-003          partition planner                         golden plan and property tests              Gate A

  FR-004          reference executor                        reference replay suite                      Gate A

  FR-005          worker registry                           register/reconnect integration              Gate B/C

  FR-006          scheduler assignment transaction          lease state-machine and concurrency tests   Gate B

  FR-007          heartbeat service                         stale/current epoch ordering tests          Gate B

  FR-008          worker artifact staging                   crash-before/after-fsync scenarios          Gate B

  FR-009          commit service and database constraints   commit race matrix                          Gate B

  FR-010          commit rejection and artifact cleanup     losing-attempt scenario                     Gate B

  FR-011          expiry/retry service                      retry classification and limit tests        Gate B

  FR-012          run finalizer and merge                   all-task terminal and digest verification   Gate B

  FR-013          cancellation service and worker control   cancel/complete ordering matrix             Gate B

  FR-014          startup reconciliation                    coordinator crash matrix                    Gate B/E

  FR-015          canonical result manifest                 worker-count and rerun equality             Gate A

  FR-016          kernel registry                           unknown/version/parameter tests             Gate A

  FR-017          queues and configured bounds              slow-consumer/resource tests                Gate C

  FR-018          status query and CLI                      snapshot/status integration tests           Gate B/C

  FR-019          structured logging adapters               schema and correlation tests                Gate B/E

  FR-020          metrics registry/export                   metric definition and bounded-label tests   Gate E

  FR-021          protocol encoder/decoder                  fragmentation, limits, fuzz                 Gate C

  FR-022          async UDS server/client                   independent-process integration             Gate C

  FR-023          TCP transport adapter                     loopback/private-network experiment         optional Gate E

  FR-024          cpp_core and bindings                     differential/sanitizer/crossover            Gate D

  FR-025          checkpoint exporter                       checkpoint/restart consistency              Gate E

  FR-026          diagnostic bundle                         redaction and completeness test             Gate E

  FR-027          fault scenario runner                     named deterministic crash matrix            Gate E

  FR-028          benchmark runner and analysis             raw evidence regeneration                   Gate E

  FR-029          multi-host deployment                     trusted-host scenario                       research

  FR-030          shared-memory transport experiment        equivalence/resource/perf study             research

  FR-031          straggler/speculation policy              simulation and duplicate commit tests       research

  FR-032          metadata repository adapter               backend contract suite                      research
  -----------------------------------------------------------------------------------------------------------------------

**Table 130 --- Nonfunctional-requirement traceability.**

  ----------------------------------------------------------------------------------------------------------------------------------
  Requirement     Owning mechanism                               Primary evidence                                    Target gate
  --------------- ---------------------------------------------- --------------------------------------------------- ---------------
  NFR-001         invariant registry and run finalizer           terminal-state property and recovery suite          Gate B/E

  NFR-002         reference engine and canonical merge           rerun and worker-count differential                 Gate A/E

  NFR-003         SQLite transactions and artifact publication   restart/crash matrix                                Gate B/E

  NFR-004         queue/batch/log/frame limits                   overload and soak resource assertions               Gate C/E

  NFR-005         metadata, structured events, diagnostics       timeline reconstruction test                        Gate E

  NFR-006         clock/process/transport/storage abstractions   deterministic scenario runner                       Gate E

  NFR-007         build and platform detection                   clean Linux build and explicit unsupported errors   Gate F

  NFR-008         module boundaries and typing                   lint/type/import architecture gates                 continuous

  NFR-009         benchmark manifest and claim map               release evidence audit                              Gate E/F

  NFR-010         local defaults, schemas, path policy           security test suite                                 Gate F

  NFR-011         release/evidence tooling                       clean regeneration from tag                         Gate F

  NFR-012         README, demos, operations docs                 external clean-clone review                         Gate F

  NFR-013         metrics/resource collection                    benchmark and diagnostic evidence                   Gate E

  NFR-014         schema/protocol/version modules                compatibility and migration matrix                  Gate C/F

  NFR-015         drain/cancel/shutdown lifecycle                signal and restart integration tests                Gate B/C
  ----------------------------------------------------------------------------------------------------------------------------------

## 351. Traceability Status Values

**Table 131 --- Requirement lifecycle statuses.**

  ------------------------------------------------------------------------------------------------------------
  Status                         Meaning
  ------------------------------ -----------------------------------------------------------------------------
  specified                      Contract and acceptance are written, but no implementation is claimed.

  implemented                    Code exists and local focused tests pass.

  integrated                     End-to-end behavior works across the intended component boundaries.

  evidenced                      Release-tagged test, scenario, or measurement demonstrates the requirement.

  published                      Public documentation and claim map point to the evidence.

  deferred                       Requirement is intentionally outside the current gate, with rationale.

  removed                        Requirement was superseded; history and migration are documented.
  ------------------------------------------------------------------------------------------------------------
