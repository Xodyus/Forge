# Part XIII - Security, Trust Boundaries, and Defensive Engineering

## 190. Threat Model

Forge is designed for one developer or a trusted small group on a local host or private test network. It does not safely execute hostile kernels and is not hardened for public Internet exposure. Defensive work focuses on malformed inputs, path safety, resource exhaustion, accidental secret disclosure, dependency integrity, and clear deployment defaults.

**Table 66 --- Forge trust boundaries.**

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------
  Actor or input                       Trust level                                              Defense
  ------------------------------------ -------------------------------------------------------- -----------------------------------------------------------------
  Kernel code installed with project   Trusted but buggy                                        Process supervision, limits, tests; not sandboxed.

  Client manifest                      Untrusted data within authenticated/local context        Strict schemas, bounds, registries, path policy.

  Worker messages                      Authenticated/trusted worker but may be stale or buggy   State checks, fencing, digests, protocol limits.

  Dataset files                        Registered immutable input; may be corrupt               Headers, bounds, checksums, schema validation.

  Network peer                         Local/private by default; not assumed well behaved       Handshake, max frames, timeouts, sequence, close on violations.

  Artifact paths                       Never trusted directly from peer                         Root-confined resolver and unique generated names.

  Dependencies                         Third-party supply-chain risk                            Pins, hashes where practical, updates, licenses, scanners.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------

## 191. Unsafe Deserialization Prohibition

- Do not accept pickle, cloudpickle, dill, marshal, or arbitrary Python import paths from protocol clients.
- Control payloads decode into strict primitive schemas with bounds.
- Kernels are selected from a local allow-listed registry by ID and exact version.
- Configuration loaders do not evaluate Python expressions or shell commands.
- YAML, if used, must use a safe loader; JSON or TOML is simpler for public manifests.
- Binary decoders validate lengths and versions before allocation and interpretation.

## 192. Path Traversal and Filesystem Safety

- All dataset and artifact paths resolve beneath configured roots after normalization.
- Reject absolute paths, .. components, NUL bytes, device files, FIFOs, and unexpected symlinks according to policy.
- Use generated opaque IDs for run/task/attempt directory names; never concatenate unsanitized user labels.
- Open files with exclusive/create/no-follow options where available and verify file type.
- Do not shell out with interpolated paths. Use subprocess argument arrays when tools are necessary.
- Run staging and public repository examples in non-sensitive directories.

## 193. Authentication and Authorization

For local Unix-domain deployment, filesystem permissions and optional peer credentials may be enough for the stated scope. TCP multi-host mode needs an explicit identity decision. A pre-shared token over TLS is a reasonable educational extension; inventing a custom cryptographic protocol is not.

- Bind locally by default and require an explicit unsafe or trusted-network flag for non-loopback TCP.
- Separate client submit/cancel permissions from worker register/report permissions if authentication is added.
- Never log tokens or place them in run manifests.
- Rotate or revoke test credentials through configuration without changing semantic run identity.
- Document that authentication does not sandbox trusted kernel code.

## 194. TLS Extension

- Use the standard library or a maintained TLS implementation, not custom encryption.
- Validate certificates or pinned identities according to the test deployment.
- Keep application framing inside TLS unchanged.
- Measure handshake separately from steady-state control traffic.
- Store no private key in the public repository; generate development certificates through scripts and .gitignore them.
- If TLS is not implemented, state plainly that TCP is for loopback or trusted private networks only.

## 195. Resource Exhaustion Defenses

**Table 67 --- Resource exhaustion controls.**

  ---------------------------------------------------------------------------------------------------------------------
  Resource                       Defense
  ------------------------------ --------------------------------------------------------------------------------------
  Network memory                 Hard frame and per-session buffer limits; max sessions.

  Decoded objects                Collection, string, nesting, and task-plan limits.

  Coordinator memory             Paged ready window, bounded queues, bounded caches.

  Worker memory                  Batch limits, output limits, process resource policy.

  Disk                           Admission reserve, staged-output cap, GC, diagnostics quota.

  CPU                            Task timeout, child supervision, request rate limits, bounded verification executor.

  Logs                           Size/rotation policy, rate limiting, bounded error fields.

  Database                       Task-count limits, short transactions, pagination, retention policy.
  ---------------------------------------------------------------------------------------------------------------------

## 196. Trusted Code Execution Boundary

> Forge executes locally installed Python and C++ kernels with worker privileges. It is not a sandbox. Do not submit code or data from an untrusted party. Process separation and resource limits improve fault containment but do not create a security boundary.

Place this warning in the README, configuration example, and any multi-host documentation. Do not imply that Docker alone makes arbitrary code safe.

## 197. Secrets and Sensitive Data

- No secrets belong in run manifests, dataset manifests, logs, benchmark rows, diagnostic bundles, or Git history.
- Operational credentials come from environment or secret files outside the repository and are redacted when configuration is printed.
- Public datasets are synthetic or openly licensed and contain no personal information.
- Diagnostic export uses an allow list of fields and scans for common secret patterns as a defense in depth.
- Repository history is inspected before release; deleting a secret from the latest commit is insufficient if it remains in history.

## 198. Supply-Chain and Build Integrity

- Pin direct dependencies and commit lockfiles appropriate to the Python toolchain.
- Record hashes for release artifacts and benchmark datasets.
- Use Dependabot or another update workflow, but review changes and rerun tests rather than auto-merging blindly.
- Run a dependency vulnerability scanner and document limitations and false positives.
- Review licenses for pybind11, test libraries, serialization libraries, and copied code.
- Do not copy a tutorial implementation without attribution or understanding.
- CI release jobs use least-privilege tokens and protected environments where available.

## 199. Artifact and Evidence Integrity

- Exact-byte SHA-256 digests accompany public datasets, results, raw benchmark files, and diagnostic bundles.
- Evidence manifests list source commit, build fingerprint, commands, and child file digests.
- Analysis scripts verify raw schemas and digests before plotting.
- Do not edit raw benchmark data manually. Corrections create a new file with an exclusion or annotation record.
- Release tags and generated artifacts should be signed if convenient, but signatures are optional and must not be overstated.

## 200. Logging and Error Disclosure

- Return stable error codes and bounded messages to peers; keep detailed safe context locally.
- Do not echo malformed payloads or arbitrary paths into logs without escaping and truncation.
- Strip credentials, home-directory details, and sensitive environment variables from public bundles.
- Stack traces are useful for local diagnosis but may reveal paths and configuration; redact before publication.
- Protocol errors distinguish peer fault from internal bug without revealing internal SQL or filesystem details unnecessarily.

## 201. Secure Default Checklist

- Coordinator binds to Unix-domain socket or loopback.
- TCP multi-host disabled unless explicitly configured.
- pickle and arbitrary callable submission unavailable.
- Artifact roots must exist or be created with restrictive permissions.
- Frame, plan, queue, output, and task limits have finite defaults.
- Strict path resolver and no-follow policy enabled.
- Diagnostic export redacts by default.
- Development secrets and generated certificates ignored by Git.
- Kernel trust warning visible.
- Destructive GC defaults to dry run.

## 202. Security Test Matrix

**Table 68 --- Security acceptance tests.**

  -----------------------------------------------------------------------------------------------------
  Test ID                        Acceptance case
  ------------------------------ ----------------------------------------------------------------------
  SEC-001                        Absolute, parent, symlink, and special-file paths are rejected.

  SEC-002                        Oversized frame and nested payload reject before large allocation.

  SEC-003                        pickle-like payload cannot select or instantiate code.

  SEC-004                        Unknown kernel/import path is rejected by registry.

  SEC-005                        Unregistered peer cannot request work before handshake.

  SEC-006                        Non-loopback bind requires explicit configuration.

  SEC-007                        Secrets are redacted from normalized config and diagnostic bundle.

  SEC-008                        Output and plan limits stop resource exhaustion fixtures.

  SEC-009                        Malformed protocol strings are escaped and bounded in logs.

  SEC-010                        GC cannot delete a committed artifact even under crafted path names.

  SEC-011                        Dependency and license reports are generated for release.

  SEC-012                        Public repository secret scan is clean.
  -----------------------------------------------------------------------------------------------------
