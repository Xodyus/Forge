# Contributing

This is currently a solo educational project (§266: one student engineer, ~15-20
focused hours/week). These notes exist so the workflow is documented, not because
outside contributions are expected yet.

## Before you start

Read [docs/spec/INDEX.md](docs/spec/INDEX.md) and the relevant Part file in full
before implementing any component — do not implement from memory. Read
[CLAUDE.md](CLAUDE.md) for the hard constraints, invariants, and dependency-direction
rules that bind every change.

## Workflow (§252)

- Keep `master` buildable and tested. Use short-lived feature branches and small,
  reviewable pull requests.
- Every pull request names the requirement IDs, invariants, tests, and benchmark
  impact it touches, where relevant.
- Use consistent commit messages that explain intent, not only what changed.
- Tests before implementation. No feature may be added ahead of its position in the
  critical path (§269).

## Branch protection expectations (§271)

These are the rules `master` should be protected under once CI is green enough to
enforce them (§252: "Keep main buildable and tested"). Solo project, so this is
mostly self-discipline until/unless it's turned into a live GitHub branch protection
rule:

- No direct pushes of implementation changes to `master` — use a feature branch and a
  pull request, even solo, so the PR template's spec/invariant/test checklist gets
  filled in and there is a reviewable diff in the history.
- Required status checks before merge, once each exists and is reliably green:
  `lint-python`, `typecheck`, `unit-python`, `build-native`, `unit-native`, `smoke`
  (§258; see `.github/workflows/ci.yml`).
- Do not force-push or rewrite history on `master`. Tags for Gate A/B/benchmark
  baselines/public release are never rewritten once pushed (§252).
- A pull request that touches `cpp/` should not merge with `unit-native` failing, even
  though sanitizer jobs are not enabled yet (see the commented CI stubs and their gate
  TODOs).

## Local setup

```sh
uv sync --extra test --extra dev
pre-commit install
scripts/smoke.sh
```

## Code review checklist (§264)

- What semantic contract or invariant changes?
- Is the transaction or ownership boundary still correct?
- Can a retry, duplicate, cancellation, or restart hit this code?
- Are new queues, buffers, files, tasks, or threads bounded and owned?
- Are errors typed and classified rather than swallowed?
- Do tests cover both transaction orders or failure sides?
- Does C++ memory outlive its owner or cross the GIL boundary unsafely?
- Does the change alter benchmark comparability or require a new manifest version?
- Is documentation or an ADR required?

## Definition of done (§265)

- Acceptance statement and non-goals are written.
- Implementation is typed, formatted, linted, and reviewed.
- Unit and integration tests cover success, failure, and idempotency as applicable.
- Relevant invariants and database constraints remain green.
- Observability fields and bounds are added.
- Documentation and schemas are updated.
- Performance is measured when the change touches a hot or resource-sensitive path.
- No claim is added before evidence exists.
