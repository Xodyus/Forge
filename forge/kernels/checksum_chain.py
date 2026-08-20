"""Reference kernel 3/3: order-sensitive checksum reduction (§274 Week 4, §24).

The other two reference kernels (event counts, instrument sums) are associative and
commutative — their merge result would be identical regardless of partition order,
which makes them poor evidence that the engine actually merges in canonical ordinal
order rather than completion order (§24: "the baseline merge processes committed
partition results in ordinal order... makes behavior stable even for non-associative
operations"). This kernel is deliberately order-sensitive — a running sha256 chain
over each record's packed bytes, then a second sha256 over the ordered partition
checksums — so a merge-order bug changes the final digest instead of hiding.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence

from forge.datasets.format import EventRecord
from forge.kernels.base import canonical_json_bytes, reject_unknown_parameters

KERNEL_ID = "forge.checksum-chain"
KERNEL_VERSION = "1.0.0"
RESULT_SCHEMA_ID = "forge.checksum-chain-result"
RESULT_SCHEMA_VERSION = 1


class ChecksumChainKernel:
    kernel_id = KERNEL_ID
    kernel_version = KERNEL_VERSION
    result_schema_id = RESULT_SCHEMA_ID
    result_schema_version = RESULT_SCHEMA_VERSION

    def validate_parameters(self, parameters: Mapping[str, object]) -> None:
        reject_unknown_parameters(parameters, kernel_id=self.kernel_id)

    def execute_partition(
        self, records: Iterable[EventRecord], parameters: Mapping[str, object]
    ) -> bytes:
        hasher = hashlib.sha256()
        for record in records:
            hasher.update(record.pack())
        return canonical_json_bytes({"sha256": hasher.hexdigest()})

    def merge(
        self, ordered_partial_results: Sequence[bytes], parameters: Mapping[str, object]
    ) -> bytes:
        hasher = hashlib.sha256()
        for partial in ordered_partial_results:
            partition_hex = json.loads(partial)["sha256"]
            hasher.update(bytes.fromhex(partition_hex))
        return canonical_json_bytes({"sha256": hasher.hexdigest()})
