# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versioning follows §262 milestone
tags (`v0.1-reference`, `v0.2-durable-local`, `v0.3-sockets`, `v0.4-cpp`,
`v1.0-portfolio`) rather than strict SemVer before Gate F.

## [Unreleased]

### Added

- Week 1 repository scaffold (§251, §271): directory layout, Python package skeleton
  (docstring-only, no implementations), C++20 CMake project with four targets
  (`forge_cpp_core`, `forge_cpp_bindings`, `forge_cpp_tests`, `forge_cpp_bench`),
  CMake presets (debug/release/asan/ubsan), pre-commit config, CI job skeleton,
  one-command smoke test, and ADR templates for 0001 and 0002.
- Week 1 stretch outcomes (§271) and remaining must-have gaps: GitHub issue templates
  and PR template, branch-protection expectations (documented, not yet a live GitHub
  setting), a dev container (`.devcontainer/`, unverified locally — no Docker in this
  environment), and an mkdocs documentation site skeleton with link-checking
  (`mkdocs build --strict` via `mkdocs-htmlproofer-plugin`) wired into CI as the
  `docs` job.

### Fixed

- CI workflow triggered on `branches: [main]`, but the repository's default branch is
  `master`; push-trigger would silently never have fired.
- A line-length lint violation in `scripts/check_no_raw_benchmarks.py` left over from
  the Week 1 scaffold.
