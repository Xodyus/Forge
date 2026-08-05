<!-- §252: every pull request names requirement IDs, invariants, tests, and
     benchmark impact where relevant. §264 is the reviewer's checklist. -->

## What and why

## Spec / invariant impact

- Requirement or section:
- Invariants touched (INV-0NN) and why they still hold:

## Tests

- [ ] New/updated tests cover success, failure, and idempotency as applicable (§265)
- [ ] `scripts/smoke.sh` passes
- [ ] `ctest --preset debug` passes (if `cpp/` changed)

## Benchmark impact

- [ ] No change to a hot or resource-sensitive path
- [ ] Changed — measured, evidence attached
- [ ] Changed — not yet measured (explain why that's acceptable here)

## Review checklist (§264, self-check before requesting review)

- [ ] Transaction or ownership boundary is still correct
- [ ] Can a retry, duplicate, cancellation, or restart hit this code? If so, tested.
- [ ] New queues/buffers/files/tasks/threads are bounded and owned
- [ ] Errors are typed and classified, not swallowed
- [ ] Documentation or an ADR updated if this changes a decision
