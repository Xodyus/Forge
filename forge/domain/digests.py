"""Content digest value object (§16 ``artifact_digest``, Appendix B §353).

Schema v1 supports exactly one algorithm. Widening this later is a schema version
change (§34), not a silent format extension.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

SUPPORTED_ALGORITHM = "sha256"


@dataclass(frozen=True, slots=True)
class Digest:
    algorithm: str
    hex_value: str

    def __post_init__(self) -> None:
        if self.algorithm != SUPPORTED_ALGORITHM:
            raise ValueError(f"only {SUPPORTED_ALGORITHM} is supported in schema v1")
        if len(self.hex_value) != 64:
            raise ValueError("invalid sha256 digest length")
        try:
            int(self.hex_value, 16)
        except ValueError as exc:
            raise ValueError("digest hex_value must be hexadecimal") from exc

    @classmethod
    def of_bytes(cls, data: bytes) -> Digest:
        return cls(algorithm=SUPPORTED_ALGORITHM, hex_value=hashlib.sha256(data).hexdigest())

    def __str__(self) -> str:
        return f"{self.algorithm}:{self.hex_value}"
