"""forge.transport — In-process, Unix-domain, and TCP session implementations.

Responsibility: backpressure and lifecycle for framed forge.protocol messages.
Boundary: implements the sockets and queues that forge.protocol stays independent of;
consumed by forge.coordinator and forge.worker (§38, §40,
docs/spec/part-03-architecture.md).
"""
