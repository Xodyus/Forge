"""Reference kernel 1/3: event counts, total and by `event_type` (§274 Week 4)."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from forge.datasets.format import EventRecord
from forge.kernels.base import canonical_json_bytes, reject_unknown_parameters

KERNEL_ID = "forge.event-counts"
KERNEL_VERSION = "1.0.0"
RESULT_SCHEMA_ID = "forge.event-counts-result"
RESULT_SCHEMA_VERSION = 1


class EventCountsKernel:
    kernel_id = KERNEL_ID
    kernel_version = KERNEL_VERSION
    result_schema_id = RESULT_SCHEMA_ID
    result_schema_version = RESULT_SCHEMA_VERSION

    def validate_parameters(self, parameters: Mapping[str, object]) -> None:
        reject_unknown_parameters(parameters, kernel_id=self.kernel_id)

    def execute_partition(
        self, records: Iterable[EventRecord], parameters: Mapping[str, object]
    ) -> bytes:
        by_event_type: Counter[int] = Counter()
        total = 0
        for record in records:
            by_event_type[record.event_type] += 1
            total += 1
        return canonical_json_bytes(
            {
                "total": total,
                "by_event_type": {str(k): v for k, v in by_event_type.items()},
            }
        )

    def merge(
        self, ordered_partial_results: Sequence[bytes], parameters: Mapping[str, object]
    ) -> bytes:
        total = 0
        by_event_type: Counter[str] = Counter()
        for partial in ordered_partial_results:
            data = json.loads(partial)
            total += data["total"]
            by_event_type.update(data["by_event_type"])
        return canonical_json_bytes({"total": total, "by_event_type": dict(by_event_type)})
