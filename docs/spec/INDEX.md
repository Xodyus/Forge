# Forge Master Build Specification — Index

Source: `Forge_Master_Build_Specification.docx` (v1.0, 2026-07-22), converted with pandoc
and split by Part/Appendix. All 434 numbered sections (§1–§434) are covered, contiguous,
and non-overlapping across the files below. Section numbers are global across the whole
document, not reset per Part. Figures referenced by section text live in
[media/](media/).

**Consult this table before implementing any component.** Read the relevant Part file
in full before writing code against it — do not implement from memory or from this
index's one-line descriptions alone.

| Sections  | File                                                                     | Description |
|-----------|--------------------------------------------------------------------------|--------------|
| (front matter) | [part-00-document-control.md](part-00-document-control.md)         | Revision history, how to use this document, navigation map, relevance to target internship. |
| §1–§13    | [part-01-product-definition.md](part-01-product-definition.md)           | Part I — Product thesis, scope, users, requirements, release gates, and success rubric. |
| §14–§34   | [part-02-execution-model.md](part-02-execution-model.md)                 | Part II — Execution vocabulary, manifests, partitioning, determinism, leases, retries, commits, and invariants. |
| §35–§49   | [part-03-architecture.md](part-03-architecture.md)                       | Part III — System context, deployment modes, component boundaries, concurrency, configuration, and architecture decisions. |
| §50–§70   | [part-04-coordinator.md](part-04-coordinator.md)                         | Part IV — Coordinator lifecycle, durable state, scheduler, worker registry, leases, retries, commit protocol, and recovery. |
| §71–§85   | [part-05-worker-runtime.md](part-05-worker-runtime.md)                   | Part V — Worker runtime, process isolation, local caching, cancellation, output staging, resource accounting, and crash behavior. |
| §86–§102  | [part-06-storage-formats.md](part-06-storage-formats.md)                 | Part VI — Dataset format, event records, manifests, artifact layout, checksums, metadata schema, and storage integrity. |
| §103–§117 | [part-07-protocol.md](part-07-protocol.md)                               | Part VII — Framed protocol, Unix-domain sockets, TCP, asyncio, flow control, versioning, and optional shared memory. |
| §118–§135 | [part-08-cpp-boundary.md](part-08-cpp-boundary.md)                       | Part VIII — C++20 accelerator, pybind11 boundary, batches, buffers, GIL policy, parser, aggregators, and packaging. |
| §136–§150 | [part-09-scheduling.md](part-09-scheduling.md)                           | Part IX — Scheduling policy, partition sizing, fairness, admission control, locality, stragglers, and simulation. |
| §151–§166 | [part-10-fault-tolerance.md](part-10-fault-tolerance.md)                 | Part X — Failure taxonomy, fencing, duplicate execution, conditional commits, checkpoints, restart, and chaos testing. |
| §167–§178 | [part-11-sdk-cli.md](part-11-sdk-cli.md)                                 | Part XI — Public Python API, CLI, configuration, local debugging, examples, notebooks, and package quality. |
| §179–§189 | [part-12-observability.md](part-12-observability.md)                     | Part XII — Structured logs, metrics, traces, status views, diagnostic bundles, and operational acceptance criteria. |
| §190–§202 | [part-13-security.md](part-13-security.md)                               | Part XIII — Threat model, trust boundaries, deserialization, paths, authentication, secrets, and secure defaults. |
| §203–§223 | [part-14-verification.md](part-14-verification.md)                       | Part XIV — Unit, state-machine, property, differential, fuzz, integration, crash, chaos, and regression testing. |
| §224–§250 | [part-15-benchmarking.md](part-15-benchmarking.md)                       | Part XV — Benchmark questions, workloads, latency, throughput, scaling, profiling, analysis, and claim rules. |
| §251–§265 | [part-16-build-ci-release.md](part-16-build-ci-release.md)               | Part XVI — Repository, build system, dependencies, linting, sanitizers, CI, packaging, releases, and code review. |
| §266–§313 | [part-17-roadmap.md](part-17-roadmap.md)                                 | Part XVII — Twenty-week roadmap, epics, detailed backlog, risk register, and definitions of ready and done. |
| §314–§349 | [part-18-portfolio-evidence.md](part-18-portfolio-evidence.md)           | Part XVIII — README, demos, evidence bundle, technical presentation, resume bullets, and interview preparation. (Not enumerated in the original Navigation Map's Part list; added as its own file to keep one-Part-per-file.) |
| §350–§351 | [appendix-a.md](appendix-a.md)                                           | Appendix A — Requirements traceability matrix. |
| §352–§356 | [appendix-b.md](appendix-b.md)                                           | Appendix B — Canonical Python domain model skeleton. |
| §357–§362 | [appendix-c.md](appendix-c.md)                                           | Appendix C — Dataset and manifest formats. |
| §363–§370 | [appendix-d.md](appendix-d.md)                                           | Appendix D — SQLite metadata schema and transaction patterns. |
| §371–§378 | [appendix-e.md](appendix-e.md)                                           | Appendix E — Framed control protocol skeleton. |
| §379–§385 | [appendix-f.md](appendix-f.md)                                           | Appendix F — Worker runtime and process-supervision skeleton. |
| §386–§392 | [appendix-g.md](appendix-g.md)                                           | Appendix G — Coordinator service skeleton. |
| §393–§400 | [appendix-h.md](appendix-h.md)                                           | Appendix H — C++20 accelerator and pybind11 skeleton. |
| §401–§407 | [appendix-i.md](appendix-i.md)                                           | Appendix I — Verification harness and failure-scenario schemas. |
| §408–§414 | [appendix-j.md](appendix-j.md)                                           | Appendix J — Benchmark runner, raw evidence, and analysis skeleton. |
| §415–§422 | [appendix-k.md](appendix-k.md)                                           | Appendix K — Configuration, CLI, and operations runbook. |
| §423–§428 | [appendix-l.md](appendix-l.md)                                           | Appendix L — Review checklists, glossary (§427), and final acceptance (§428). |
| §429–§434 | [appendix-m.md](appendix-m.md)                                           | Appendix M — References and further study, plus closing engineering standard. |

## Frequently-needed sections

| §   | Topic                          | File |
|-----|---------------------------------|------|
| §1  | Project thesis                  | part-01-product-definition.md |
| §4  | Explicit non-goals               | part-01-product-definition.md |
| §13 | Scope-control rules              | part-01-product-definition.md |
| §31 | Core invariants                  | part-02-execution-model.md |
| §40 | Dependency direction              | part-03-architecture.md |
| §41 | Pure core and impure edges        | part-03-architecture.md |
| §269| Critical path                    | part-17-roadmap.md |
| §427| Glossary                          | appendix-l.md |
