"""Canonical serialization for manifest models (§17).

"Canonicalize the manifest before hashing: sorted object keys, normalized numeric
forms, UTF-8 encoding, no comments, no environment-specific absolute paths, and
explicit schema version." This module is the one place that rule is implemented so
every manifest type (dataset, experiment, run) hashes the same way.
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from forge.domain.digests import Digest


def canonical_json_bytes(model: BaseModel) -> bytes:
    data = model.model_dump(mode="json", by_alias=True)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def content_digest(model: BaseModel) -> Digest:
    return Digest.of_bytes(canonical_json_bytes(model))
