# Security

## Threat model (§190)

Forge is designed for one developer or a trusted small group on a local host or
private test network. It does not safely execute hostile kernels and is not hardened
for public Internet exposure. Defensive work focuses on malformed inputs, path safety,
resource exhaustion, accidental secret disclosure, dependency integrity, and clear
deployment defaults.

Kernel code is trusted but may be buggy: it runs with worker process privileges and is
never treated as a sandbox for untrusted input (§4, §191). Client manifests, worker
messages, dataset files, network peers, artifact paths, and third-party dependencies
are each handled according to their own trust level and defense — see
[docs/spec/part-13-security.md §190](docs/spec/part-13-security.md) for the full trust
boundary table.

## Reporting a vulnerability

This is a solo educational project. Open a GitHub issue, or, for anything that
should not be public before a fix lands, contact the maintainer directly (see the
repository owner's profile for contact details).

## Limitations

At the current Week 1 scaffold stage, no coordinator, protocol, worker, or storage
logic exists yet, so none of the defenses in
[docs/spec/part-13-security.md](docs/spec/part-13-security.md) are implemented. This
file will be expanded as each trust boundary is built.
