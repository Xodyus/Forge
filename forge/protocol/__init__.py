"""forge.protocol — Message models, framing, encoder/decoder, version negotiation.

Responsibility: transport-independent payload semantics.
Boundary: depends on forge.domain value objects; must remain usable without a live
socket, TCP connection, or in-process queue (§38, §40,
docs/spec/part-03-architecture.md).
"""
