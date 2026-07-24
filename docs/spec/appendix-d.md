# Appendix D - SQLite Metadata Schema and Transaction Patterns

## 363. Schema Principles

- Use foreign keys, uniqueness, and check constraints as executable invariants rather than relying only on application code.
- Use text UUIDs or 16-byte blobs consistently; do not mix representations casually.
- Store timestamps in an explicitly named unit and clock domain. Wall-clock timestamps aid diagnosis; live lease decisions use monotonic deadlines held in process and durable conservative recovery fields.
- Keep transactions short. Hashing, file copying, network calls, and result merge do not occur while a write transaction is open.
- Preserve attempt history. Retry creates a new attempt row rather than mutating the old attempt into a new identity.
- Treat committed artifact association as unique and immutable except through an explicit repair procedure.
- Every migration is transactional where SQLite permits and is tested from the previous public milestone.

## 364. Illustrative Core Schema

    PRAGMA foreign_keys = ON;
    PRAGMA journal_mode = WAL;
    PRAGMA synchronous = FULL;
    PRAGMA busy_timeout = 5000;

    CREATE TABLE schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at_utc TEXT NOT NULL,
        source_version TEXT NOT NULL,
        migration_sha256 TEXT NOT NULL
    );

    CREATE TABLE datasets (
        dataset_id TEXT PRIMARY KEY,
        manifest_sha256 TEXT NOT NULL UNIQUE,
        schema_id TEXT NOT NULL,
        schema_version INTEGER NOT NULL CHECK (schema_version > 0),
        manifest_json BLOB NOT NULL,
        registered_at_utc TEXT NOT NULL
    );

    CREATE TABLE experiments (
        experiment_id TEXT PRIMARY KEY,
        manifest_sha256 TEXT NOT NULL UNIQUE,
        dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id),
        kernel_id TEXT NOT NULL,
        kernel_version TEXT NOT NULL,
        engine TEXT NOT NULL CHECK (engine IN ('python', 'cpp')),
        manifest_json BLOB NOT NULL,
        registered_at_utc TEXT NOT NULL
    );

    CREATE TABLE runs (
        run_id TEXT PRIMARY KEY,
        submission_key TEXT UNIQUE,
        experiment_id TEXT NOT NULL REFERENCES experiments(experiment_id),
        state TEXT NOT NULL CHECK (
            state IN (
                'planning', 'running', 'cancelling',
                'succeeded', 'failed', 'cancelled'
            )
        ),
        created_at_utc TEXT NOT NULL,
        started_at_utc TEXT,
        terminal_at_utc TEXT,
        cancel_requested_at_utc TEXT,
        failure_code TEXT,
        canonical_result_sha256 TEXT,
        version INTEGER NOT NULL DEFAULT 0 CHECK (version >= 0)
    );

    CREATE TABLE tasks (
        task_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
        ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
        partition_id TEXT NOT NULL,
        state TEXT NOT NULL CHECK (
            state IN ('pending', 'leased', 'committed', 'failed', 'cancelled')
        ),
        current_fencing_epoch INTEGER NOT NULL DEFAULT 0
            CHECK (current_fencing_epoch >= 0),
        committed_attempt_id TEXT,
        failure_code TEXT,
        version INTEGER NOT NULL DEFAULT 0 CHECK (version >= 0),
        UNIQUE (run_id, ordinal),
        UNIQUE (run_id, partition_id)
    );

    CREATE TABLE workers (
        worker_id TEXT PRIMARY KEY,
        first_seen_at_utc TEXT NOT NULL,
        last_seen_at_utc TEXT NOT NULL,
        disabled INTEGER NOT NULL DEFAULT 0 CHECK (disabled IN (0, 1)),
        labels_json BLOB NOT NULL
    );

    CREATE TABLE worker_sessions (
        session_id TEXT PRIMARY KEY,
        worker_id TEXT NOT NULL REFERENCES workers(worker_id),
        process_id INTEGER,
        host_id TEXT NOT NULL,
        protocol_major INTEGER NOT NULL,
        protocol_minor INTEGER NOT NULL,
        state TEXT NOT NULL CHECK (
            state IN ('connecting', 'ready', 'draining', 'closed', 'failed')
        ),
        connected_at_utc TEXT NOT NULL,
        disconnected_at_utc TEXT,
        capabilities_json BLOB NOT NULL
    );

    CREATE TABLE attempts (
        attempt_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
        attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
        worker_id TEXT NOT NULL REFERENCES workers(worker_id),
        session_id TEXT REFERENCES worker_sessions(session_id),
        fencing_epoch INTEGER NOT NULL CHECK (fencing_epoch > 0),
        state TEXT NOT NULL CHECK (
            state IN (
                'assigned', 'running', 'staged', 'committed',
                'failed', 'expired', 'cancelled', 'rejected_stale'
            )
        ),
        assigned_at_utc TEXT NOT NULL,
        started_at_utc TEXT,
        staged_at_utc TEXT,
        terminal_at_utc TEXT,
        lease_deadline_utc TEXT NOT NULL,
        error_class TEXT,
        error_code TEXT,
        exit_code INTEGER,
        term_signal INTEGER,
        version INTEGER NOT NULL DEFAULT 0 CHECK (version >= 0),
        UNIQUE (task_id, attempt_number),
        UNIQUE (task_id, fencing_epoch)
    );

    CREATE TABLE artifacts (
        artifact_id TEXT PRIMARY KEY,
        attempt_id TEXT NOT NULL UNIQUE
            REFERENCES attempts(attempt_id) ON DELETE CASCADE,
        state TEXT NOT NULL CHECK (
            state IN ('staged', 'committed', 'quarantined', 'deleted')
        ),
        relative_path TEXT NOT NULL UNIQUE,
        byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
        sha256 TEXT NOT NULL,
        schema_id TEXT NOT NULL,
        schema_version INTEGER NOT NULL CHECK (schema_version > 0),
        created_at_utc TEXT NOT NULL,
        committed_at_utc TEXT,
        deleted_at_utc TEXT
    );

    CREATE TABLE coordinator_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emitted_at_utc TEXT NOT NULL,
        run_id TEXT,
        task_id TEXT,
        attempt_id TEXT,
        worker_id TEXT,
        event_type TEXT NOT NULL,
        payload_json BLOB NOT NULL
    );

    CREATE INDEX idx_tasks_schedulable
        ON tasks(run_id, state, ordinal);
    CREATE INDEX idx_attempts_task_state
        ON attempts(task_id, state);
    CREATE INDEX idx_attempts_lease_deadline
        ON attempts(state, lease_deadline_utc);
    CREATE INDEX idx_events_run_id
        ON coordinator_events(run_id, event_id);

## 365. Foreign-Key Cycle for Committed Attempt

The illustrative schema leaves `tasks.committed_attempt_id` without an immediate foreign key because `attempts` already references `tasks`, and migration order plus cyclic integrity require care. The final design should enforce the relationship with a deferred foreign key where supported by the chosen schema structure, a separate `task_results` table with unique `task_id`, or a trigger plus application transaction tests. The preferred clearer option is a separate result table.

    CREATE TABLE task_results (
        task_id TEXT PRIMARY KEY
            REFERENCES tasks(task_id) ON DELETE CASCADE,
        attempt_id TEXT NOT NULL UNIQUE
            REFERENCES attempts(attempt_id),
        artifact_id TEXT NOT NULL UNIQUE
            REFERENCES artifacts(artifact_id),
        fencing_epoch INTEGER NOT NULL CHECK (fencing_epoch > 0),
        committed_at_utc TEXT NOT NULL,
        result_sha256 TEXT NOT NULL
    );

## 366. Assignment Transaction Pseudocode

    BEGIN IMMEDIATE;

    -- 1. Verify worker/session is active and run is admitting work.
    -- 2. Select one eligible pending task using deterministic policy.
    -- 3. Increment fencing epoch while task is still pending.
    UPDATE tasks
    SET state = 'leased',
        current_fencing_epoch = current_fencing_epoch + 1,
        version = version + 1
    WHERE task_id = :task_id
      AND state = 'pending'
      AND EXISTS (
          SELECT 1 FROM runs
          WHERE runs.run_id = tasks.run_id
            AND runs.state = 'running'
      );

    -- Require exactly one changed row.

    INSERT INTO attempts (
        attempt_id,
        task_id,
        attempt_number,
        worker_id,
        session_id,
        fencing_epoch,
        state,
        assigned_at_utc,
        lease_deadline_utc
    )
    SELECT
        :attempt_id,
        task_id,
        :attempt_number,
        :worker_id,
        :session_id,
        current_fencing_epoch,
        'assigned',
        :now_utc,
        :lease_deadline_utc
    FROM tasks
    WHERE task_id = :task_id
      AND state = 'leased';

    COMMIT;

## 367. Conditional Commit Transaction Pseudocode

    BEGIN IMMEDIATE;

    -- Validate and register the staged artifact before this transaction or insert
    -- its descriptor here without performing file I/O while the lock is held.

    INSERT INTO task_results (
        task_id,
        attempt_id,
        artifact_id,
        fencing_epoch,
        committed_at_utc,
        result_sha256
    )
    SELECT
        t.task_id,
        a.attempt_id,
        ar.artifact_id,
        a.fencing_epoch,
        :now_utc,
        ar.sha256
    FROM tasks AS t
    JOIN attempts AS a ON a.task_id = t.task_id
    JOIN artifacts AS ar ON ar.attempt_id = a.attempt_id
    WHERE t.task_id = :task_id
      AND a.attempt_id = :attempt_id
      AND a.fencing_epoch = :fencing_epoch
      AND t.current_fencing_epoch = :fencing_epoch
      AND t.state = 'leased'
      AND a.state = 'staged'
      AND ar.state = 'staged'
      AND NOT EXISTS (
          SELECT 1 FROM task_results r WHERE r.task_id = t.task_id
      );

    -- Require exactly one inserted row; zero means stale, duplicate, invalid state,
    -- or cancellation and must be classified with a read-only diagnostic query.

    UPDATE artifacts
    SET state = 'committed', committed_at_utc = :now_utc
    WHERE artifact_id = :artifact_id
      AND state = 'staged';

    UPDATE attempts
    SET state = 'committed', terminal_at_utc = :now_utc,
        version = version + 1
    WHERE attempt_id = :attempt_id
      AND state = 'staged'
      AND fencing_epoch = :fencing_epoch;

    UPDATE tasks
    SET state = 'committed', version = version + 1
    WHERE task_id = :task_id
      AND state = 'leased'
      AND current_fencing_epoch = :fencing_epoch;

    COMMIT;

## 368. Lease Expiry Transaction Pattern

    BEGIN IMMEDIATE;

    UPDATE attempts
    SET state = 'expired',
        terminal_at_utc = :now_utc,
        error_class = 'worker_lost',
        error_code = 'LEASE_EXPIRED',
        version = version + 1
    WHERE attempt_id = :attempt_id
      AND state IN ('assigned', 'running', 'staged')
      AND fencing_epoch = :expected_epoch
      AND lease_deadline_utc <= :now_utc;

    -- If the attempt changed and retry policy permits, return the logical task to
    -- pending. Do not decrement or reuse the fencing epoch.
    UPDATE tasks
    SET state = 'pending', version = version + 1
    WHERE task_id = :task_id
      AND state = 'leased'
      AND current_fencing_epoch = :expected_epoch
      AND NOT EXISTS (
          SELECT 1 FROM task_results r WHERE r.task_id = tasks.task_id
      );

    COMMIT;

## 369. Database Diagnostic Queries

    -- Tasks marked committed without a result row.
    SELECT t.task_id, t.run_id
    FROM tasks t
    LEFT JOIN task_results r ON r.task_id = t.task_id
    WHERE t.state = 'committed' AND r.task_id IS NULL;

    -- More than one nonterminal attempt for one task.
    SELECT task_id, COUNT(*) AS active_attempts
    FROM attempts
    WHERE state IN ('assigned', 'running', 'staged')
    GROUP BY task_id
    HAVING COUNT(*) > 1;

    -- A committed result whose epoch is not the task's current epoch.
    SELECT r.task_id, r.fencing_epoch, t.current_fencing_epoch
    FROM task_results r
    JOIN tasks t ON t.task_id = r.task_id
    WHERE r.fencing_epoch <> t.current_fencing_epoch;

    -- Staged artifacts older than retention threshold and not referenced.
    SELECT ar.*
    FROM artifacts ar
    LEFT JOIN task_results r ON r.artifact_id = ar.artifact_id
    WHERE ar.state = 'staged'
      AND r.artifact_id IS NULL
      AND ar.created_at_utc < :cutoff_utc;

    -- Terminal run with nonterminal tasks.
    SELECT r.run_id, r.state, COUNT(*) AS nonterminal_tasks
    FROM runs r
    JOIN tasks t ON t.run_id = r.run_id
    WHERE r.state IN ('succeeded', 'failed', 'cancelled')
      AND t.state IN ('pending', 'leased')
    GROUP BY r.run_id, r.state;

## 370. SQLite Operational Settings

**Table 134 --- SQLite starting policy.**

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Setting                Recommended starting policy                     Reason and caution
  ---------------------- ----------------------------------------------- ----------------------------------------------------------------------------------------------------------------
  journal_mode           WAL                                             Readers do not block writer in the same way; still one writer and WAL lifecycle must be managed.

  synchronous            FULL for durability study                       Stronger fsync behavior; NORMAL may be an explicit benchmark variant, not silent default.

  foreign_keys           ON for every connection                         SQLite does not enforce unless enabled per connection.

  busy_timeout           bounded, e.g. 5 s                               Avoid immediate transient failure, but long waits need metrics and cancellation awareness.

  transaction mode       BEGIN IMMEDIATE for write decision paths        Acquire write intent early and make contention visible; keep transactions short.

  WAL checkpoint         controlled and observed                         Avoid unbounded WAL growth; do not checkpoint unpredictably inside latency-sensitive path without measurement.

  connection ownership   one connection per owning thread/task context   Do not share unsafely; encapsulate usage.

  integrity check        startup/release/diagnostic policy               Full checks may be expensive; distinguish quick and deep modes.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
