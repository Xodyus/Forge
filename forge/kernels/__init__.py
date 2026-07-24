"""forge.kernels — Python kernel registry and reference implementations.

Responsibility: trusted, versioned computations dispatched by forge.worker.
Boundary: kernels run with worker process privileges and are treated as trusted code,
never as a sandbox for untrusted input (§4, §38, docs/spec/part-03-architecture.md).
"""
