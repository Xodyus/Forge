# Appendix F - Worker Runtime and Process-Supervision Skeleton

## 379. Worker Runtime Decomposition

**Table 138 --- Worker runtime ownership.**

  ---------------------------------------------------------------------------------------------------------------------
  Component            Owns                                                   Must not own
  -------------------- ------------------------------------------------------ -----------------------------------------
  WorkerService        connection, registration, slot accounting, shutdown    kernel implementation or database state

  AssignmentManager    accepted grants and bounded pending queue              durable lease truth

  AttemptSupervisor    one child process lifecycle and result channel         coordinator commit authority

  AttemptChild         dataset read, kernel execution, attempt output         network protocol or final publication

  ArtifactStager       attempt directory, atomic files, descriptor/checksum   task-level committed path

  HeartbeatReporter    progress/resource snapshots and cancellation receipt   lease extension decision

  LocalCache           validated immutable file reuse and eviction            authoritative dataset identity

  LogCapture           bounded child stdout/stderr and structured metadata    unbounded in-memory accumulation
  ---------------------------------------------------------------------------------------------------------------------

## 380. Attempt Outcome Envelope

    from dataclasses import dataclass
    from typing import Literal


    @dataclass(frozen=True, slots=True)
    class AttemptMetrics:
        wall_ns: int
        cpu_user_ns: int | None
        cpu_system_ns: int | None
        peak_rss_bytes: int | None
        bytes_read: int
        bytes_written: int
        records_processed: int


    @dataclass(frozen=True, slots=True)
    class AttemptSucceeded:
        kind: Literal["succeeded"]
        artifact: ArtifactDescriptor
        metrics: AttemptMetrics


    @dataclass(frozen=True, slots=True)
    class AttemptFailed:
        kind: Literal["failed"]
        error: ErrorEnvelope
        metrics: AttemptMetrics | None
        exit_code: int | None
        signal_number: int | None


    AttemptOutcome = AttemptSucceeded | AttemptFailed

## 381. Child Process Entry Point

    from __future__ import annotations

    import os
    import traceback
    from multiprocessing.connection import Connection
    from pathlib import Path


    def attempt_child_main(
        grant_bytes: bytes,
        result_connection: Connection,
        attempt_root: str,
    ) -> None:
        """Top-level spawn-safe child entry point."""
        try:
            grant = decode_and_validate_grant(grant_bytes)
            root = Path(attempt_root).resolve(strict=True)
            attempt_directory = safe_attempt_directory(root, grant.attempt_id)
            attempt_directory.mkdir(mode=0o750, parents=False, exist_ok=False)

            kernel = KERNEL_REGISTRY.resolve(grant.kernel).factory()
            kernel.validate_parameters(decode_parameters(grant.kernel))

            batches = read_validated_batches(grant.partition)
            partial_result = kernel.execute_batches(
                batches,
                decode_parameters(grant.kernel),
            )
            artifact = stage_partial_result(
                attempt_directory,
                grant,
                partial_result,
            )
            outcome: AttemptOutcome = AttemptSucceeded(
                kind="succeeded",
                artifact=artifact,
                metrics=collect_attempt_metrics(),
            )
            result_connection.send_bytes(encode_outcome(outcome))
        except BaseException as exc:
            # The final implementation should classify expected errors separately,
            # bound traceback bytes, and avoid leaking secrets or arbitrary objects.
            envelope = ErrorEnvelope(
                code="ATTEMPT_CHILD_FAILURE",
                classification=ErrorClass.INTERNAL,
                message=str(exc),
                retryable=False,
                details={
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc(limit=30)[-16_384:],
                },
            )
            try:
                result_connection.send_bytes(
                    encode_outcome(
                        AttemptFailed(
                            kind="failed",
                            error=envelope,
                            metrics=collect_attempt_metrics_best_effort(),
                            exit_code=None,
                            signal_number=None,
                        )
                    )
                )
            except BaseException:
                pass
            raise
        finally:
            result_connection.close()
            os._exit(0)  # replace with deliberate final exit policy in real code

The final child entry point should not use `os._exit(0)` blindly after raising; this skeleton intentionally highlights the need for an explicit exit policy. A production-quality educational implementation should choose exit codes for success, typed failure, protocol failure, and internal crash, flush the result channel deliberately, and let the supervisor classify missing or malformed outcomes.

## 382. Attempt Supervisor Skeleton

    from __future__ import annotations

    import asyncio
    import multiprocessing as mp
    from dataclasses import dataclass
    from multiprocessing.connection import Connection
    from pathlib import Path
    import signal
    import time


    @dataclass(slots=True)
    class SupervisedProcess:
        process: mp.Process
        result_reader: Connection
        started_monotonic: float
        terminate_sent: bool = False
        kill_sent: bool = False


    class AttemptSupervisor:
        def __init__(
            self,
            *,
            attempt_root: Path,
            graceful_cancel_seconds: float = 5.0,
            terminate_seconds: float = 3.0,
        ) -> None:
            self._context = mp.get_context("spawn")
            self._attempt_root = attempt_root
            self._graceful_cancel_seconds = graceful_cancel_seconds
            self._terminate_seconds = terminate_seconds

        def start(self, grant_bytes: bytes) -> SupervisedProcess:
            reader, writer = self._context.Pipe(duplex=False)
            process = self._context.Process(
                target=attempt_child_main,
                args=(grant_bytes, writer, str(self._attempt_root)),
                daemon=False,
            )
            process.start()
            writer.close()
            return SupervisedProcess(
                process=process,
                result_reader=reader,
                started_monotonic=time.monotonic(),
            )

        async def wait(
            self,
            supervised: SupervisedProcess,
            *,
            timeout_seconds: float,
            cancellation: asyncio.Event,
        ) -> AttemptOutcome:
            deadline = time.monotonic() + timeout_seconds
            try:
                while True:
                    if supervised.result_reader.poll():
                        data = supervised.result_reader.recv_bytes(MAX_OUTCOME_BYTES)
                        outcome = decode_and_validate_outcome(data)
                        await asyncio.to_thread(supervised.process.join, 1.0)
                        if supervised.process.is_alive():
                            await self._force_stop(supervised)
                        return outcome

                    if not supervised.process.is_alive():
                        await asyncio.to_thread(supervised.process.join)
                        return classify_process_exit(supervised.process.exitcode)

                    if cancellation.is_set():
                        await self._cancel(supervised)
                        return cancelled_outcome(supervised.process.exitcode)

                    if time.monotonic() >= deadline:
                        await self._cancel(supervised)
                        return timeout_outcome(supervised.process.exitcode)

                    await asyncio.sleep(0.05)
            finally:
                supervised.result_reader.close()
                if supervised.process.is_alive():
                    await self._force_stop(supervised)
                await asyncio.to_thread(supervised.process.join)

        async def _cancel(self, supervised: SupervisedProcess) -> None:
            # A separate cooperative control channel is preferable. Signal use is
            # platform-specific and must be guarded and tested.
            if supervised.process.is_alive() and supervised.process.pid is not None:
                try:
                    signal_process_group(
                        supervised.process.pid,
                        signal.SIGTERM,
                    )
                    supervised.terminate_sent = True
                except ProcessLookupError:
                    return
            await asyncio.to_thread(
                supervised.process.join,
                self._graceful_cancel_seconds,
            )
            if supervised.process.is_alive():
                await self._force_stop(supervised)

        async def _force_stop(self, supervised: SupervisedProcess) -> None:
            if supervised.process.is_alive():
                supervised.process.kill()
                supervised.kill_sent = True
                await asyncio.to_thread(
                    supervised.process.join,
                    self._terminate_seconds,
                )

## 383. Supervisor Review Questions

- Who owns the child object and guarantees `join()` on every return and exception path?
- Can the child create grandchildren, and if so, how is the process group terminated safely?
- Can a PID be reused between observation and signal? What ownership evidence is checked?
- What happens when the result message is valid but the process exits nonzero, or vice versa?
- How large may the child outcome be, and can the pipe deadlock because the parent waits for exit before draining?
- Does cancellation race with successful outcome receipt, and which outcome wins under the written contract?
- Can a worker shutdown leave attempt directories or cache locks behind?
- How are stdout and stderr drained without blocking the child or consuming unbounded memory?
- Which metrics are sampled before process exit, and which may be unavailable after a crash?
- How does the supervisor behave if its own worker process receives SIGTERM?

## 384. Worker Main Loop Pseudocode

    async def worker_main(config: WorkerConfig) -> None:
        service = WorkerService(config)
        await service.connect_and_register()
        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(service.connection_reader())
                group.create_task(service.connection_writer())
                group.create_task(service.heartbeat_loop())
                group.create_task(service.assignment_loop())
                group.create_task(service.status_loop())
                await service.stopped.wait()
        except* ProtocolError as errors:
            service.record_protocol_failure(errors)
            raise
        finally:
            await service.begin_drain(reason="worker shutdown")
            await service.cancel_or_wait_for_active_attempts()
            await service.close_connection()
            service.verify_no_live_children()

## 385. Worker Cache Policy

**Table 139 --- Worker cache policy.**

  -------------------------------------------------------------------------------------------------------------------------------------------
  Concern                        Policy
  ------------------------------ ------------------------------------------------------------------------------------------------------------
  Key                            Dataset or artifact content digest plus schema identity; never path alone.

  Validation                     Verify size and digest on insertion; optional sampled/full revalidation policy on hit.

  Mutability                     Cached content is read-only and never reused as an attempt output path.

  Capacity                       Byte and entry limits with visible current/eviction metrics.

  Eviction                       LRU or simple age policy; never evict an actively pinned file.

  Concurrency                    Per-digest lock or atomic temp/rename; duplicate downloads may be tolerated but partial visibility is not.

  Corruption                     Quarantine/delete cache entry, emit diagnostic, and refetch or fail according to source availability.

  Cleanup                        Best effort at startup and steady state; cache loss cannot invalidate durable run semantics.
  -------------------------------------------------------------------------------------------------------------------------------------------
