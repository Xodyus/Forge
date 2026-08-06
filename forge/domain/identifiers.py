"""Identifier types (§16, Table 10).

Identifiers are opaque in APIs but structured enough for logs and storage. Authority
must never be derived from identifier ordering or shape.

- ``RunId``/``TaskId``/``AttemptId``/``WorkerId``/``ArtifactId`` are UUID-backed:
  each is created once by the coordinator (run, attempt) or a stable installation
  policy (worker) and never reused after a terminal state.
- ``PartitionId`` is a plain string, not a UUID: §19 requires it to be a
  deterministic function of the run's partition plan, reproducible by the reference
  path, Python workers, C++ workers, retries, and recovery without coordinator
  assignment.
- ``DatasetId``/``ExperimentId`` are plain strings because §16 allows content- or
  client-derived identity (e.g. a content-addressed dataset id) rather than requiring
  a coordinator-minted UUID.
"""

from __future__ import annotations

from typing import NewType
from uuid import UUID

RunId = NewType("RunId", UUID)
TaskId = NewType("TaskId", UUID)
AttemptId = NewType("AttemptId", UUID)
WorkerId = NewType("WorkerId", UUID)
ArtifactId = NewType("ArtifactId", UUID)

PartitionId = NewType("PartitionId", str)
DatasetId = NewType("DatasetId", str)
ExperimentId = NewType("ExperimentId", str)
