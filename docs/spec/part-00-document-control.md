# Forge

## Master Build Specification for a Deterministic Distributed Event-Replay and Compute Engine in Python and C++20

Prepared for Lucas Cochran \| Version 1.0 \| July 22, 2026

An educational distributed-systems portfolio project: define the guarantees, make failure observable, measure the bottleneck, and report only what the evidence supports.

> Scope and independence notice. Forge is an original educational project and is not affiliated with Hudson River Trading or any other employer. It is a local-first research-compute simulator, not a production cluster manager, not a cloud service, and not a safe sandbox for executing untrusted code.
>
> Truthfulness rule. Do not place a feature, throughput number, scaling claim, recovery guarantee, technology, or optimization on a resume until a tagged repository and reproducible evidence support the exact wording. A smaller system with explicit semantics and convincing tests is stronger than a larger system described vaguely.

# Document Control

## Revision History

**Table 1 --- Document revision history.**

  --------------------------------------------------------------------------------------------------------------------------------------------------------------
  Version      Date         Owner           Status        Summary
  ------------ ------------ --------------- ------------- ------------------------------------------------------------------------------------------------------
  1.0          2026-07-22   Lucas Cochran   Master plan   Initial product, architecture, implementation, verification, benchmark, and portfolio specification.

  1.1          TBD          Lucas Cochran   Planned       Record semantic decisions and implementation deviations after Gate A.

  2.0          TBD          Lucas Cochran   Planned       Freeze the public portfolio release and evidence bundle.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------

## How to Use This Master Document

This document is simultaneously a product requirements document, execution-semantics contract, architecture specification, implementation playbook, failure-recovery design, verification plan, benchmark protocol, project-management backlog, and portfolio-release checklist. It should be read differently at each stage of the project.

- **Before coding:** read Parts I through IV, select the Gate A scope, and write architecture decision records for the execution, storage, and commit semantics. Do not begin with shared memory, multi-host networking, or speculative scheduling.
- **During implementation:** convert requirement IDs and backlog items into issues. Each pull request should identify the requirement, invariant, or failure mode it changes and should add tests before changing performance-sensitive code.
- **During recovery work:** treat failures as normal state transitions rather than exceptional anecdotes. A worker disappearing, a lease expiring, a duplicate attempt finishing, or a coordinator restarting must produce a defined and testable outcome.
- **During performance work:** freeze the benchmark workload and environment before changing implementation. Profile first, preserve a baseline, publish raw outputs, and document neutral or negative experiments.
- **Before publishing:** use the evidence map, public-release gate, demo script, resume-claim checklist, and interview questions. A public repository is an argument about engineering judgment; every visible claim needs proof.

The recommended dependency order is conservative: explicit semantics, immutable dataset format, single-process reference path, durable coordinator, worker recovery, C++ acceleration, transport improvements, multi-process scaling, fault injection, and only then optional multi-host or shared-memory work.

## Navigation Map

**Table 2 --- Document navigation map.**

  ---------------------------------------------------------------------------------------------------------------------------------------------------------
  Location                       Contents
  ------------------------------ --------------------------------------------------------------------------------------------------------------------------
  Part I                         Product thesis, scope, users, requirements, release gates, and success rubric.

  Part II                        Execution vocabulary, manifests, partitioning, determinism, leases, retries, commits, and invariants.

  Part III                       System context, deployment modes, component boundaries, concurrency, configuration, and architecture decisions.

  Part IV                        Coordinator lifecycle, durable state, scheduler, worker registry, leases, retries, commit protocol, and recovery.

  Part V                         Worker runtime, process isolation, local caching, cancellation, output staging, resource accounting, and crash behavior.

  Part VI                        Dataset format, event records, manifests, artifact layout, checksums, metadata schema, and storage integrity.

  Part VII                       Framed protocol, Unix-domain sockets, TCP, asyncio, flow control, versioning, and optional shared memory.

  Part VIII                      C++20 accelerator, pybind11 boundary, batches, buffers, GIL policy, parser, aggregators, and packaging.

  Part IX                        Scheduling policy, partition sizing, fairness, admission control, locality, stragglers, and simulation.

  Part X                         Failure taxonomy, fencing, duplicate execution, conditional commits, checkpoints, restart, and chaos testing.

  Part XI                        Public Python API, CLI, configuration, local debugging, examples, notebooks, and package quality.

  Part XII                       Structured logs, metrics, traces, status views, diagnostic bundles, and operational acceptance criteria.

  Part XIII                      Threat model, trust boundaries, deserialization, paths, authentication, secrets, and secure defaults.

  Part XIV                       Unit, state-machine, property, differential, fuzz, integration, crash, chaos, and regression testing.

  Part XV                        Benchmark questions, workloads, latency, throughput, scaling, profiling, analysis, and claim rules.

  Part XVI                       Repository, build system, dependencies, linting, sanitizers, CI, packaging, releases, and code review.

  Part XVII                      Twenty-week roadmap, epics, detailed backlog, risk register, and definitions of ready and done.

  Part XVIII                     README, demos, evidence bundle, technical presentation, resume bullets, and interview preparation.

  Appendices                     Schemas, starter code, SQL, configurations, commands, templates, checklists, glossary, and references.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------

## Why Forge Is Relevant to the Target Internship

HRT currently describes its Summer 2027 software-engineering internship as work on real C++ and Python projects that contribute to its trading and research environment. Its public campus interview guidance emphasizes idiomatic programming, efficient resource use, systems fundamentals such as memory, I/O, and process management, data structures, methodical problem solving, collaboration, and communication. A 2025 intern-project article describes work involving streaming APIs, high-performance data services, compression, and C++/Python infrastructure. Those public materials motivate the engineering signals this project is designed to demonstrate. They do not imply that Forge resembles HRT's proprietary architecture or that completing Forge guarantees an interview. \[HRT-1\] \[HRT-2\] \[HRT-3\]

Forge is intentionally broader than a typical multiprocessing tutorial. Its differentiating work is not merely launching workers. The project requires precise task semantics, durable coordination, bounded queues, idempotent publication, deterministic replay, fault injection, a measured C++ boundary, and a written account of tradeoffs. These are original project recommendations derived from general distributed-systems principles and the hiring signals described above.
