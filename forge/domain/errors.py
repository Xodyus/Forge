"""Error classification and the domain error envelope (§23 Table 13, Appendix B §355).

Retry policy is a decision (``retry_decision`` in §41's pure-core table), not a fixed
property of a class — the same ``ErrorClass`` can be retryable or not depending on
attempt history and policy. This module only carries the classification tag and the
bounded, loggable envelope; the decision function is Week 7 (E05) work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorClass(StrEnum):
    """Error classes and default retry policy (§23 Table 13)."""

    VALIDATION = "validation"
    DETERMINISTIC_KERNEL = "deterministic_kernel"
    TRANSIENT_WORKER = "transient_worker"
    LEASE_LOSS = "lease_loss"
    STORAGE_PUBLICATION = "storage_publication"
    PROTOCOL = "protocol"
    CANCELLATION = "cancellation"
    INTERNAL_INVARIANT = "internal_invariant"


@dataclass(frozen=True, slots=True)
class ErrorEnvelope:
    code: str
    classification: ErrorClass
    message: str
    retryable: bool
    details: dict[str, Any] = field(default_factory=dict)

    def public_dict(self) -> dict[str, Any]:
        """Bounded, non-secret fields suitable for protocol messages or logs."""
        return {
            "code": self.code,
            "classification": self.classification.value,
            "message": self.message[:1_024],
            "retryable": self.retryable,
            "details": self.details,
        }


class IllegalTransitionError(RuntimeError):
    """Raised when a state machine is asked to make an unsupported move."""
