# Part XVI - Build System, CI, Packaging, Documentation, and Release Engineering

## 251. Repository Layout

    forge/
      pyproject.toml
      CMakeLists.txt
      CMakePresets.json
      README.md
      LICENSE
      SECURITY.md
      CONTRIBUTING.md
      CHANGELOG.md
      uv.lock or equivalent
      cmake/
      cpp/
      forge/
      tests/
      examples/
      docs/
        architecture/
        adr/
        semantics/
        benchmarks/
        postmortems/
      scripts/
      benchmarks/
        workloads/
        raw/
        reports/
      .github/workflows/

## 252. Git and Branch Strategy

- Keep main buildable and tested. Use short-lived feature branches and small reviewable pull requests.
- Every pull request names requirement IDs, invariants, tests, and benchmark impact where relevant.
- Use conventional or consistent commit messages that explain intent, not only changed files.
- Tag Gate A, Gate B, benchmark baselines, and public release.
- Do not rewrite published evidence tags.
- Large generated datasets, build outputs, secrets, and raw transient profiles are ignored; curated benchmark evidence may use release assets or an appropriate data location.

## 253. Python Project Configuration

- Use a PEP 517 build backend and one dependency-management workflow documented for contributors.
- Declare a supported Python range deliberately and test it.
- Separate runtime, C++ build, test, documentation, and benchmark optional dependencies.
- Include py.typed and package data explicitly.
- Expose forge and worker/coordinator entry points through project scripts.
- Lock dependencies for reproducible development and CI while keeping declared ranges reasonable.

## 254. CMake Targets and Presets

**Table 82 --- CMake targets and presets.**

  -----------------------------------------------------------------------------------------------------------------
  Target/preset                  Purpose
  ------------------------------ ----------------------------------------------------------------------------------
  forge_cpp_core                 Native parser and aggregation library without Python dependency where practical.

  forge_cpp_bindings             pybind11 extension module.

  forge_cpp_tests                GoogleTest or Catch2 native unit tests.

  forge_cpp_bench                Native microbenchmarks.

  dev-debug                      Debug symbols, assertions, high warnings.

  dev-release                    Optimized local build with symbols.

  asan-ubsan                     Sanitized native and extension tests.

  coverage                       Coverage instrumentation.

  benchmark                      Release flags, assertions policy, no sanitizer.
  -----------------------------------------------------------------------------------------------------------------

## 255. Compiler and Warning Policy

- Compile as C++20 with extensions disabled unless a documented Linux-specific feature is required.
- Enable broad warnings for project targets and treat them as errors in CI.
- Do not apply warning-as-error to third-party headers blindly.
- Use explicit signed/unsigned conversions, narrowing checks, and format-safe logging.
- Keep optimization flags in CMake presets rather than source-specific pragmas initially.
- Record compiler and flags in build_info and benchmark fingerprint.

## 256. Formatting, Linting, and Static Analysis

**Table 83 --- Static quality tools.**

  ----------------------------------------------------------------------------------------------------------
  Tool class                     Recommended role
  ------------------------------ ---------------------------------------------------------------------------
  Ruff/formatter                 Python style, imports, common bug patterns, complexity guardrails.

  mypy or pyright                Strict public API and core domain typing.

  clang-format                   Consistent C++ formatting checked in CI.

  clang-tidy                     Selected correctness, performance, modernization, and readability checks.

  CMake formatter/linter         Optional; avoid unreadable build files.

  Markdown/link checker          Documentation links and formatting.

  SQL migration checks           Migration order, checksum, and test application.

  secret scanner                 Prevent credentials and keys from entering commits.
  ----------------------------------------------------------------------------------------------------------

## 257. Dependency Policy

- Prefer standard library and small focused dependencies where they reduce risk meaningfully.
- Pin pybind11, test framework, serializer, CLI, and schema dependencies through the lockfile.
- Record why each runtime dependency exists.
- Avoid adding a full distributed framework that hides the mechanisms Forge is intended to demonstrate.
- Review changelogs and rerun compatibility, fuzz, and benchmark tests for major upgrades.
- Generate a software bill of materials or dependency report for release if practical.

## 258. CI Job Matrix

**Table 84 --- Continuous-integration jobs.**

  -----------------------------------------------------------------------------------------
  Job                            Checks
  ------------------------------ ----------------------------------------------------------
  lint-python                    format, Ruff, import rules

  typecheck                      mypy/pyright strict core packages

  unit-python                    fast unit and schema tests

  property-smoke                 bounded state-machine and generated corpus

  build-cpp                      debug and release native/extension builds

  unit-cpp                       native tests

  sanitizers                     ASan/UBSan native and Python integration

  integration-embedded           local multiprocess small fixture

  integration-unix               socket-connected coordinator/workers

  recovery-smoke                 selected crash points

  protocol-fuzz-smoke            bounded corpus/minutes

  examples                       README and example commands

  docs                           build docs, validate links and diagrams

  package                        sdist/wheel or source build install in clean environment

  security                       secret scan, dependency/license report

  benchmark-smoke                broad catastrophic-regression threshold
  -----------------------------------------------------------------------------------------

## 259. CI Runtime Tiers

**Table 85 --- CI and validation tiers.**

  -------------------------------------------------------------------------------------------------------------------------------------------------
  Tier            Cadence              Target duration                   Contents
  --------------- -------------------- --------------------------------- --------------------------------------------------------------------------
  pre-commit      developer            under 1 minute                    format, lint changed files, focused unit tests

  pull request    every PR             under 15 minutes where possible   unit, type, builds, smoke integration, sanitizers split in parallel

  nightly         scheduled            longer                            large property corpus, fuzz time, full crash matrix, multi-version tests

  release         tag candidate        as needed                         clean installs, full evidence, docs, security, reproducibility checks

  benchmark       controlled machine   study-defined                     not ordinary shared CI; publishes raw evidence
  -------------------------------------------------------------------------------------------------------------------------------------------------

## 260. Container and Environment Reproducibility

- Provide a development container or Dockerfile for toolchain convenience, not as the only supported environment.
- Pin base image by digest for release evidence when practical.
- Document host requirements for perf, process signals, shared memory, and CPU affinity because containers may restrict them.
- Do not compare bare-metal and container benchmark results without labeling.
- Use containers to prove clean builds and examples; use a controlled host for serious performance studies.

## 261. Documentation Set

**Table 86 --- Required documentation set.**

  -----------------------------------------------------------------------------------------------------------
  Document                       Required content
  ------------------------------ ----------------------------------------------------------------------------
  README                         thesis, quick start, architecture, guarantees, demo, evidence, limitations

  semantics.md                   run/task/attempt/lease/commit/cancellation contracts and invariants

  architecture.md                components, flows, deployment modes, ownership, decisions

  protocol.md                    frame, messages, versions, limits, error codes

  storage.md                     dataset, artifact, metadata, checkpoint formats and integrity

  testing.md                     test tiers, fault injection, fuzzing, reproduction

  benchmarks.md                  methodology, workload manifests, raw schema, claim rules

  operations.md                  start, stop, status, diagnostics, GC, recovery behavior

  security.md                    trust model, safe defaults, reporting, limitations

  ADRs                           decision context, alternatives, consequences, revisit triggers

  postmortems                    selected bugs or experiments with evidence and learning
  -----------------------------------------------------------------------------------------------------------

## 262. Release Versioning

- Use semantic versioning for the public package only after API expectations are clear; pre-1.0 releases may change rapidly but still use tags.
- Tag milestone releases such as v0.1-reference, v0.2-durable-local, v0.3-sockets, v0.4-cpp, and v1.0-portfolio.
- Each release notes implemented capabilities, deferred items, migrations, known limitations, and evidence links.
- Dataset, protocol, result, and metadata schema versions remain independent explicit identifiers.
- A benchmark claim cites an immutable source tag and evidence bundle digest, not latest main.

## 263. Release Checklist

- Clean checkout builds and installs in documented environments.
- All required CI, nightly, sanitizer, fuzz, integration, and recovery jobs are green.
- Database migrations apply from the previous milestone and a fresh database.
- Examples and demo script run with small generated data.
- Public artifacts and raw evidence have digests and manifests.
- Secret, license, dependency, and metadata scans are reviewed.
- README claims match implemented features and tagged evidence.
- No placeholder metrics, fake screenshots, personal paths, or local-only assumptions remain undisclosed.
- Changelog and known limitations are current.

## 264. Code Review Checklist

- What semantic contract or invariant changes?
- Is the transaction or ownership boundary still correct?
- Can a retry, duplicate, cancellation, or restart hit this code?
- Are new queues, buffers, files, tasks, or threads bounded and owned?
- Are errors typed and classified rather than swallowed?
- Do tests cover both transaction orders or failure sides?
- Does C++ memory outlive its owner or cross the GIL boundary unsafely?
- Does the change alter benchmark comparability or require a new manifest version?
- Is documentation or an ADR required?

## 265. Definition of Done for an Engineering Change

- Acceptance statement and non-goals are written.
- Implementation is typed, formatted, linted, and reviewed.
- Unit and integration tests cover success, failure, and idempotency as applicable.
- Relevant invariants and database constraints remain green.
- Observability fields and bounds are added.
- Documentation and schemas are updated.
- Performance is measured when the change touches a hot or resource-sensitive path.
- No claim is added before evidence exists.
