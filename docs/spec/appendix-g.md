# Appendix G - Coordinator Service Skeleton

## 386. Repository Interface

    from __future__ import annotations

    from collections.abc import Sequence
    from dataclasses import dataclass
    from typing import Protocol


    @dataclass(frozen=True, slots=True)
    class AssignmentRequest:
        worker_id: WorkerId
        session_id: str
        supported_engines: frozenset[str]
        free_slots: int


    @dataclass(frozen=True, slots=True)
    class CommitDecision:
        committed: bool
        reason: str
        existing_artifact: ArtifactDescriptor | None = None


    class CoordinatorRepository(Protocol):
        def submit_run(
            self,
            *,
            submission_key: str | None,
            experiment_manifest: bytes,
        ) -> RunId: ...

        def plan_tasks(
            self,
            run_id: RunId,
            partitions: Sequence[PartitionDescriptor],
        ) -> None: ...

        def assign_one(
            self,
            request: AssignmentRequest,
            *,
            now_utc: str,
            lease_deadline_utc: str,
        ) -> LeaseGrant | None: ...

        def renew_leases(
            self,
            worker_id: WorkerId,
            renewals: Sequence[tuple[AttemptId, int]],
            *,
            now_utc: str,
            new_deadline_utc: str,
        ) -> dict[AttemptId, bool]: ...

        def stage_artifact(
            self,
            attempt_id: AttemptId,
            fencing_epoch: int,
            artifact: ArtifactDescriptor,
        ) -> None: ...

        def commit_attempt(
            self,
            attempt_id: AttemptId,
            fencing_epoch: int,
            artifact_id: ArtifactId,
            *,
            now_utc: str,
        ) -> CommitDecision: ...

        def fail_attempt(
            self,
            attempt_id: AttemptId,
            fencing_epoch: int,
            error: ErrorEnvelope,
        ) -> None: ...

        def expire_due_leases(self, *, now_utc: str, limit: int) -> int: ...

        def request_cancellation(self, run_id: RunId, *, now_utc: str) -> bool: ...

        def reconcile_startup(self, *, now_utc: str) -> "RecoveryReport": ...

## 387. Scheduler Loop Skeleton

    class CoordinatorService:
        def __init__(
            self,
            repository: CoordinatorRepository,
            config: CoordinatorConfig,
            clock: Clock,
        ) -> None:
            self._repository = repository
            self._config = config
            self._clock = clock
            self._stopping = asyncio.Event()

        async def lease_sweeper(self) -> None:
            while not self._stopping.is_set():
                started = self._clock.monotonic()
                try:
                    expired = await asyncio.to_thread(
                        self._repository.expire_due_leases,
                        now_utc=self._clock.utc_iso(),
                        limit=self._config.lease_sweep_batch,
                    )
                    METRICS.lease_expirations.increment(expired)
                except Exception:
                    LOGGER.exception("lease sweep failed")
                    METRICS.lease_sweep_failures.increment()
                elapsed = self._clock.monotonic() - started
                delay = max(0.0, self._config.lease_sweep_interval - elapsed)
                try:
                    await asyncio.wait_for(self._stopping.wait(), timeout=delay)
                except TimeoutError:
                    pass

        async def handle_poll(
            self,
            request: AssignmentRequest,
        ) -> LeaseGrant | None:
            if request.free_slots <= 0:
                return None
            now = self._clock.utc_now()
            grant = await asyncio.to_thread(
                self._repository.assign_one,
                request,
                now_utc=now.isoformat(),
                lease_deadline_utc=(
                    now + self._config.lease_duration
                ).isoformat(),
            )
            if grant is not None:
                LOGGER.info(
                    "task leased",
                    extra=log_context(grant),
                )
                METRICS.assignments.increment()
            return grant

## 388. Commit Handler Skeleton

    async def handle_attempt_staged(
        self,
        message: AttemptStagedMessage,
    ) -> CommitDecision:
        # Validate descriptor fields and resolve the path beneath the artifact root.
        descriptor = validate_artifact_descriptor(message.artifact)

        # Verify the file before entering the write transaction. Re-check immutable
        # identity in the transaction through descriptor fields; never hash while
        # holding the database writer lock.
        await asyncio.to_thread(
            verify_staged_artifact,
            self._config.artifact_root,
            descriptor,
        )

        try:
            await asyncio.to_thread(
                self._repository.stage_artifact,
                message.attempt_id,
                message.fencing_epoch,
                descriptor,
            )
            decision = await asyncio.to_thread(
                self._repository.commit_attempt,
                message.attempt_id,
                message.fencing_epoch,
                descriptor.artifact_id,
                now_utc=self._clock.utc_iso(),
            )
        except StaleAttemptError:
            decision = CommitDecision(
                committed=False,
                reason="stale_attempt",
            )

        if decision.committed:
            await self._publication_service.ensure_visible(descriptor)
            METRICS.commits.increment()
        else:
            await self._cleanup_service.mark_losing_attempt(descriptor)
            METRICS.commit_rejections.labels(decision.reason).increment()
        return decision

The order between database commit and final file publication must be selected consistently. The skeleton above separates them for clarity but is not a complete crash-safe protocol. The final implementation must use the staged-versus-visible states defined earlier, write a transaction marker or result row that startup reconciliation understands, and test failure before and after each publication step. Never claim a task is committed if its contract requires a visible file that has not been durably published.

## 389. Startup Reconciliation Skeleton

    @dataclass(frozen=True, slots=True)
    class RecoveryReport:
        uncertain_attempts: int
        expired_attempts: int
        tasks_requeued: int
        staged_artifacts: int
        orphaned_artifacts: int
        missing_committed_artifacts: int
        fatal_errors: tuple[str, ...]


    async def start_coordinator(config: CoordinatorConfig) -> CoordinatorService:
        repository = SqliteCoordinatorRepository.open(config.database_path)
        repository.apply_migrations()
        repository.verify_constraints_and_schema()

        artifact_report = await asyncio.to_thread(
            scan_artifact_root,
            config.artifact_root,
            limits=config.recovery_scan_limits,
        )
        report = await asyncio.to_thread(
            repository.reconcile_startup,
            now_utc=utc_now_iso(),
        )
        combined = reconcile_metadata_and_files(report, artifact_report)
        write_recovery_report(config.diagnostics_root, combined)

        if combined.missing_committed_artifacts:
            raise StartupIntegrityError(
                "committed artifacts are missing; see recovery report"
            )
        if combined.fatal_errors:
            raise StartupIntegrityError(
                "metadata or artifact integrity check failed"
            )

        service = CoordinatorService(repository, config, SystemClock())
        await service.start_listeners()
        return service

## 390. Coordinator Invariant Assertions

    def assert_run_invariants(snapshot: RunSnapshot) -> None:
        for task in snapshot.tasks:
            results = snapshot.results_by_task.get(task.task_id, ())
            active_attempts = [
                attempt
                for attempt in snapshot.attempts_by_task.get(task.task_id, ())
                if attempt.state in {
                    AttemptState.ASSIGNED,
                    AttemptState.RUNNING,
                    AttemptState.STAGED,
                }
            ]

            if len(results) > 1:
                raise AssertionError("task has more than one visible result")
            if task.state is TaskState.COMMITTED and len(results) != 1:
                raise AssertionError("committed task lacks exactly one result")
            if results and results[0].fencing_epoch != task.current_fencing_epoch:
                raise AssertionError("committed result has stale fencing epoch")
            if task.state is TaskState.PENDING and active_attempts:
                raise AssertionError("pending task has an active attempt")
            if task.state in {
                TaskState.COMMITTED,
                TaskState.FAILED,
                TaskState.CANCELLED,
            } and active_attempts:
                raise AssertionError("terminal task has active attempt")

        if snapshot.run.state is RunState.SUCCEEDED:
            if any(task.state is not TaskState.COMMITTED for task in snapshot.tasks):
                raise AssertionError("successful run has noncommitted task")
            if snapshot.run.canonical_result_sha256 is None:
                raise AssertionError("successful run has no canonical digest")

## 391. Scheduler Fairness Starting Policy

A simple scheduler is easier to reason about and benchmark. Begin with pull-based assignment, per-run admission limits, and round-robin selection among runnable runs. Within a run, select the lowest deterministic task ordinal that satisfies worker capabilities. Add priorities or locality only after the base policy has simulation and starvation evidence.

    select_run:
        eligible = runs where state == RUNNING and active_leases < run_limit
        rotate from durable/in-memory fair cursor
        skip runs whose global/user admission bucket is exhausted

    select_task:
        pending tasks ordered by ordinal
        filter by required engine and declared resource profile
        select first task and assign inside one write transaction

    on_no_work:
        return bounded retry delay with jitter guidance
        do not hold a long-poll database transaction

## 392. Coordinator Shutdown Sequence

1.  Set coordinator state to draining and stop accepting new submissions if policy requires.
2.  Stop issuing new leases while continuing heartbeats and commit handling for existing attempts.
3.  Notify workers to drain; optionally request cancellation based on shutdown mode.
4.  Wait a bounded interval for active attempts and commits, keeping protocol and sweeper alive.
5.  Persist final coordinator event and checkpoint or WAL state according to policy.
6.  Close listeners so no new sessions connect, then close existing connections after bounded flush.
7.  Stop background sweep, GC, status, and metrics tasks in dependency order.
8.  Close database connection after all repository calls have completed.
9.  Remove owned socket file only after verifying it belongs to this coordinator instance.
10. Exit nonzero if shutdown left an integrity failure, but leave restartable durable state.
