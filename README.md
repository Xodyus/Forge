# Forge

> Scope and independence notice. Forge is an original educational project and is not
> affiliated with Hudson River Trading or any other employer. It is a local-first
> research-compute simulator, not a production cluster manager, not a cloud service,
> and not a safe sandbox for executing untrusted code.
>
> Truthfulness rule. Do not place a feature, throughput number, scaling claim,
> recovery guarantee, technology, or optimization on a resume until a tagged
> repository and reproducible evidence support the exact wording. A smaller system
> with explicit semantics and convincing tests is stronger than a larger system
> described vaguely.

## Project thesis (§1)

Forge will be a deterministic, local-first event-replay and compute engine written
primarily in Python, with a modern C++20 extension for performance-critical parsing
and aggregation. A client defines an immutable dataset and an experiment. The
coordinator converts the experiment into deterministic partitions and tasks, leases
those tasks to workers, accepts staged outputs, and makes one result per task visible
through a conditional commit. Workers may crash or execute the same task more than
once, but completed runs remain reproducible and committed outputs remain unambiguous.

The project is not judged by the number of distributed-systems terms in its README. It
is judged by whether another engineer can answer five concrete questions from code and
evidence: Is the execution contract precise? Is failure engineered? Is the
implementation understandable? Is performance measured? Are claims honest?

Full specification: [docs/spec/INDEX.md](docs/spec/INDEX.md). Constraints that bind
every change: [CLAUDE.md](CLAUDE.md).

## Status

This repository is at the Week 1 scaffold stage (§271): repository layout, build
system, and tooling only. No coordinator, protocol, scheduling, storage-format, or
kernel logic exists yet.

Gate checklist (§268):

- [ ] Gate 0 — Contract frozen (Week 2)
- [ ] Gate A — Deterministic reference (Week 4)
- [ ] Gate B — Durable local execution (Week 8)
- [ ] Gate C — Protocol-connected runtime (Week 11)
- [ ] Gate D — Measured native acceleration (Week 14)
- [ ] Gate E — Failure and performance study (Week 17)
- [ ] Gate F — Portfolio release (Week 20)

## Build

Requires Python 3.11–3.13, a C++20 compiler, CMake ≥3.26, Ninja, and
[uv](https://docs.astral.sh/uv/).

```sh
uv sync --extra test --extra dev
```

This builds the `forge_cpp` native extension via `scikit-build-core` and installs
Forge editable into `.venv`.

To build and run the standalone C++ test/bench targets directly (no Python needed):

```sh
cmake --preset debug -DFORGE_BUILD_BINDINGS=OFF
cmake --build --preset debug --target forge_cpp_tests
ctest --preset debug
```

## Smoke test

One command, from a clean clone, proves the build and binding path work end to end
(§271 acceptance demonstration):

```sh
scripts/smoke.sh
```

It builds the native extension, imports `forge` and `forge_cpp`, calls the trivial
scaffold function, and runs one Python and one C++ unit test.

## Repository layout

See [docs/spec/part-16-build-ci-release.md §251](docs/spec/part-16-build-ci-release.md)
for the canonical layout and [docs/spec/INDEX.md](docs/spec/INDEX.md) for the full
specification index.
