"""The reference-engine Kernel protocol and registry (§20, Appendix B §356).

§20's inline sketch and Appendix B §356's registry code describe slightly different
shapes — §20 has `run_partition`/`merge`; Appendix B has `execute_batches` over
`memoryview` batches with no merge step at all. Neither is complete on its own, and
Appendix B explicitly disclaims itself as "a design skeleton, not a drop-in complete
implementation." This module combines them: `execute_partition`/`merge` (§20's
two-phase shape, since a reference engine needs both a per-partition step and a
cross-partition merge) operating on `EventRecord` objects rather than raw
`memoryview` batches (Appendix B's batch-oriented abstraction is what the *native*
boundary needs — §41 says "measure the Python implementation before choosing the
C++ boundary," so committing to that abstraction now, in Week 4, would be getting
ahead of Week 13).

Partial and final results are plain `bytes` — canonical JSON per kernel, not a
generic object graph — matching §106's "start JSON, measure, decide on MessagePack;
pickle is prohibited" and §20's "declared result schemas" requirement.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from forge.datasets.format import EventRecord


def canonical_json_bytes(data: object) -> bytes:
    """Same canonicalization rule as `forge.domain.canonical` (sorted keys, compact
    separators, UTF-8) but over plain JSON-able data rather than a pydantic model —
    kernels shouldn't need a pydantic dependency just to produce a partial result."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


class KernelParameterError(ValueError):
    """Raised by `validate_parameters` when parameters are unknown or malformed."""


def reject_unknown_parameters(parameters: Mapping[str, object], *, kernel_id: str) -> None:
    if parameters:
        raise KernelParameterError(
            f"{kernel_id} takes no parameters, got {sorted(parameters.keys())}"
        )


class Kernel(Protocol):
    kernel_id: str
    kernel_version: str
    result_schema_id: str
    result_schema_version: int

    def validate_parameters(self, parameters: Mapping[str, object]) -> None: ...

    def execute_partition(
        self, records: Iterable[EventRecord], parameters: Mapping[str, object]
    ) -> bytes: ...

    def merge(
        self, ordered_partial_results: Sequence[bytes], parameters: Mapping[str, object]
    ) -> bytes: ...


@dataclass(frozen=True, slots=True)
class RegisteredKernel:
    kernel_id: str
    kernel_version: str
    engine: str  # "python" or "cpp" — every Week 4 kernel is "python"
    factory: Callable[[], Kernel]


class KernelRegistry:
    """Maps `(kernel_id, kernel_version, engine)` to a kernel factory. A registry,
    not a global dict, so tests can build an isolated set of kernels instead of
    depending on process-wide registration order (§20: "trusted registered kernels
    rather than accepting arbitrary pickled callables... makes function identity,
    compatibility, validation, and reproducibility explicit")."""

    def __init__(self) -> None:
        self._kernels: dict[tuple[str, str, str], RegisteredKernel] = {}

    def register(self, kernel: RegisteredKernel) -> None:
        key = (kernel.kernel_id, kernel.kernel_version, kernel.engine)
        if key in self._kernels:
            raise ValueError(f"duplicate kernel registration: {key}")
        self._kernels[key] = kernel

    def resolve(self, *, kernel_id: str, kernel_version: str, engine: str) -> Kernel:
        key = (kernel_id, kernel_version, engine)
        try:
            registered = self._kernels[key]
        except KeyError as exc:
            raise LookupError(f"unsupported kernel: {key}") from exc
        return registered.factory()
