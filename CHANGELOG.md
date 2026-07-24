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
