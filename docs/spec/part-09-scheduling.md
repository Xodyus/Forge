# Part IX - Scheduling Policy, Partition Sizing, and Load Control

## 136. Scheduling Assumptions

- The baseline workload consists of independent map tasks over immutable partitions followed by one deterministic merge.
- Workers pull work and normally execute one task at a time.
- Task durations may vary because of partition size, data distribution, page-cache state, worker load, and failure.
- The coordinator is a single logical scheduler and does not require distributed consensus for Gate A or B.
- Fairness is required across simultaneous runs, but hard real-time deadlines are not.
- Data locality is advisory because all local workers can read the shared dataset; multi-host locality is optional.
- Scheduling decisions are allowed to differ across runs while logical output remains deterministic.

## 137. Pull Versus Push Scheduling

**Table 54 --- Pull and push scheduling tradeoffs.**

  -------------------------------------------------------------------------------------------------------------------------------------
  Dimension             Pull baseline                             Push alternative
  --------------------- ----------------------------------------- ---------------------------------------------------------------------
  Capacity knowledge    Worker asks only when slot is available   Coordinator must track and predict available capacity.

  Disconnected worker   No new request arrives                    Assignments can race with disconnect and require delivery recovery.

  Backpressure          Natural at work-request boundary          Requires explicit per-worker queue bounds.

  Assignment latency    May wait for next request                 Can push immediately when task becomes ready.

  Complexity            Lower and easier to test                  Higher; potentially useful at larger scale.

  Recommendation        Use for public baseline                   Research only after scheduler overhead is measured.
  -------------------------------------------------------------------------------------------------------------------------------------

## 138. Baseline Scheduling Key

A deterministic eligibility order makes tests and incident analysis easier, even though live completion timing still affects which worker receives which task.

    candidate order = (
        run_priority descending,
        virtual_runtime ascending,
        run_created_sequence ascending,
        retry_not_before ascending,
        stage_priority ascending,
        partition_ordinal ascending,
        task_id ascending
    )

The scheduler filters by run state, task state, retry time, worker capability, resource profile, and deployment constraints. The metadata lease transaction performs the final recheck.

## 139. Fairness Across Runs

Pure FIFO can let one large run monopolize every worker. A simple weighted round-robin or virtual-runtime policy is sufficient for the project and provides a meaningful data-structure and policy discussion.

- Maintain a bounded set of runnable runs and per-run ready queues or metadata cursors.
- Increment virtual runtime by task cost estimate divided by run weight when a lease is issued or completed according to chosen policy.
- Use equal weights by default. Priority changes are administrative and recorded.
- Reserve no hidden slots for a specific run unless explicitly configured.
- Test starvation bounds with many short and long runs.
- A fairness policy affects assignment order, not canonical merge order or result.

## 140. Resource Profiles and Compatibility

**Table 55 --- Task resource profile fields.**

  ------------------------------------------------------------------------------------------------------------------------------
  Profile field        Examples                                  Use
  -------------------- ----------------------------------------- ---------------------------------------------------------------
  kernel capability    telemetry.stats python/cpp version        Worker must advertise exact compatible implementation.

  memory estimate      512 MiB, 2 GiB                            Admission and worker slot decision.

  temporary disk       result upper bound and staging overhead   Prevent predictable disk exhaustion.

  CPU class            generic x86-64, AVX2 optional             Select compatible extension path without mislabeling results.

  platform             linux-x86_64                              Reject unsupported task/worker combinations.

  exclusive flag       true for benchmark task                   Avoid local concurrency that invalidates measurements.

  expected duration    coarse bucket                             Lease sizing, fairness cost, and straggler policy.
  ------------------------------------------------------------------------------------------------------------------------------

Resource estimates are hints unless enforced. Record estimate error so the project can discuss why static estimates are difficult. The baseline should avoid pretending to schedule memory exactly.

## 141. Admission Control

- Reject or queue submissions whose manifest, partition count, artifact estimate, or requested limits exceed configured maxima.
- Limit active runs separately from historical runs.
- Limit total active leases and per-run active leases.
- Check free staging space against a conservative reserve before issuing tasks that may produce large output.
- Expose admission rejections with stable reasons and current configured limits.
- Do not rely on worker backpressure alone; the coordinator must prevent an unlimited task backlog from becoming an unlimited in-memory object graph.

## 142. Partition Size Selection

Partition size is one of the most important experiment variables. Small partitions improve load balance and failure recovery granularity but increase planning, scheduling, protocol, open/close, digest, and merge overhead. Large partitions reduce overhead but create stragglers, longer retry work, coarser cancellation, and larger peak memory.

**Table 56 --- Partition-size diagnostic guide.**

  ------------------------------------------------------------------------------------------------------------------------------------------------------
  Symptom                                  Likely partition issue              Experiment
  ---------------------------------------- ----------------------------------- -------------------------------------------------------------------------
  Coordinator CPU high with no-op kernel   Partitions too small                Increase records/task while holding total records fixed.

  One worker finishes much later           Partitions too large or data skew   Decrease partition size; inspect per-partition input distribution.

  Recovery repeats minutes of work         Partitions too large                Measure lost-work bytes and retry duration.

  Output merge dominates                   Too many result files/groups        Increase partition size or use hierarchical merge as a later extension.

  Memory spikes                            Batch or partition loaded whole     Stream batches within partition; decouple batch from partition size.
  ------------------------------------------------------------------------------------------------------------------------------------------------------

Benchmark a logarithmic range such as 10 thousand, 100 thousand, 1 million, and 10 million records per task. Do not tune against only one dataset size.

## 143. Cost Estimation

- Baseline cost equals record_count or byte_length because it is deterministic and available before execution.
- Record actual duration, selected records, groups, bytes, cache status, and worker implementation after completion.
- A later model may estimate cost from partition features, but it must not become a machine-learning side project.
- Never use prior attempt duration as authority for retry semantics; it only informs scheduling.
- Estimate error should be plotted to support a discussion of skew and scheduler limits.

## 144. Data Locality and Cache Affinity

On one host, all workers share the page cache, so assigning a partition to the same worker may not improve physical I/O. A worker-local verified cache matters more in multi-host mode or when decompressed/indexed data is cached.

- Keep locality as a tie-breaker after correctness, eligibility, fairness, and retry timing.
- Advertise immutable cache digests rather than arbitrary path lists.
- Never delay work indefinitely waiting for a preferred worker.
- Measure cold and warm cache separately, including OS page cache controls and limitations.
- If using shared storage across hosts, record network and storage topology in benchmark fingerprints.

## 145. Straggler Detection

A straggler is a task attempt that is materially slower than comparable attempts, not merely one that has run longer than an arbitrary fixed threshold.

- Compare progress rate or elapsed time against completed tasks from the same kernel, partition-size bucket, and implementation.
- Require a minimum runtime and enough peer samples before classifying a straggler.
- Separate slow input, slow compute, slow output, and blocked commit using phase metrics.
- First response is diagnosis. Speculative execution is optional and only safe after duplicate-attempt semantics are proven.
- Do not kill a slow attempt merely because a duplicate starts; allow the conditional commit race policy to decide or cancel the loser after a winner.

## 146. Speculative Execution Extension

Speculation demonstrates duplicate execution and fencing well, but it can waste resources and distort benchmark results. Keep it disabled by default.

1.  Identify a current long-running attempt that meets the straggler policy.
2.  Ensure the task allows another attempt and a separate worker has capacity.
3.  Create a new attempt with a newer fencing generation or a special concurrent-speculation authority model. The simpler model revokes the old lease, but that turns speculation into retry rather than a true race.
4.  If supporting simultaneous valid attempts, change commit eligibility explicitly so either may stage and the first transaction wins.
5.  After a winner commits, send cancellation to the loser and clean its staging output.
6.  Record duplicate compute time and whether speculation improved completion latency.

True simultaneous speculative attempts complicate the single-current-lease invariant. A safer educational alternative is late retry after lease revocation. If implementing true speculation, write a separate ADR and update invariants, schema, and tests before coding.

## 147. Work Stealing Extension

Worker-to-worker work stealing is not recommended for the public baseline because the coordinator already owns tasks and leases. A coordinator-mediated worker request is simpler and preserves authority. A simulation may compare centralized ready queues against decentralized stealing, but production-like implementation is optional.

## 148. Trusted Multi-Host Mode

- Use TCP and an artifact adapter whose consistency and atomic-publication semantics are documented.
- Worker paths cannot refer to coordinator-local filesystem locations unless a shared mount with identical namespace is guaranteed.
- Record host identity, network interface, storage mount, and clock diagnostics.
- Lease and fencing semantics do not depend on synchronized worker clocks.
- Network partitions produce the same stale-attempt outcome as disconnect on one host.
- Do not call the system secure or highly available merely because two machines participate.

## 149. Scheduler Simulation Harness

Before adding complex fairness or speculation, build a deterministic discrete-event simulator using the same pure scheduling policy and synthetic task durations.

- Simulated time advances to the next submission, worker request, completion, failure, or lease expiry.
- Scenarios vary run sizes, task costs, worker speeds, failures, and cache hints.
- Metrics include makespan, mean and p99 run completion, fairness, idle time, retries, duplicate work, and queue depth.
- Golden scenarios make policy changes reviewable without launching processes.
- The simulator is not performance evidence for the actual runtime; it is policy evidence.

## 150. Scheduler Acceptance Criteria

- No worker receives an incompatible task or more active work than accepted capacity.
- No task receives two baseline active leases concurrently.
- Fairness tests show bounded progress for several simultaneous runs.
- Ready-task memory remains bounded for large plans.
- Retry-not-before and cancellation are respected under races.
- Partition-size studies identify the overhead/load-balance tradeoff with raw data.
- Optional locality or speculation is disabled by default and has independent tests and metrics.
- A deterministic simulator covers starvation, worker loss, and long-tail scenarios.
