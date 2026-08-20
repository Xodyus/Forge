"""Reference kernel 2/3: keyed aggregation, `value_i64` summed by `instrument_id`
(§274 Week 4).

Sums as Python ints (arbitrary precision, no overflow) rather than floats — §24:
"Floating-point reductions require special care... [p]refer integer or exact
statistics for the first public kernel." `value_i64` is already an integer field, so
this kernel gets exactness for free instead of needing a documented summation-order
tolerance.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from forge.datasets.format import EventRecord
from forge.kernels.base import canonical_json_bytes, reject_unknown_parameters

KERNEL_ID = "forge.instrument-sum"
KERNEL_VERSION = "1.0.0"
RESULT_SCHEMA_ID = "forge.instrument-sum-result"
RESULT_SCHEMA_VERSION = 1


class InstrumentSumKernel:
    kernel_id = KERNEL_ID
    kernel_version = KERNEL_VERSION
    result_schema_id = RESULT_SCHEMA_ID
    result_schema_version = RESULT_SCHEMA_VERSION

    def validate_parameters(self, parameters: Mapping[str, object]) -> None:
        reject_unknown_parameters(parameters, kernel_id=self.kernel_id)

    def execute_partition(
        self, records: Iterable[EventRecord], parameters: Mapping[str, object]
    ) -> bytes:
        sums: dict[int, int] = defaultdict(int)
        for record in records:
            sums[record.instrument_id] += record.value_i64
        return canonical_json_bytes({"sums": {str(k): v for k, v in sums.items()}})

    def merge(
        self, ordered_partial_results: Sequence[bytes], parameters: Mapping[str, object]
    ) -> bytes:
        sums: dict[str, int] = defaultdict(int)
        for partial in ordered_partial_results:
            for instrument_id, value in json.loads(partial)["sums"].items():
                sums[instrument_id] += value
        return canonical_json_bytes({"sums": dict(sums)})
