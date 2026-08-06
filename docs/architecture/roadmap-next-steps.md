# Roadmap — Next Steps

`project-decisions.md` is frozen by its own rule (project charter,
Sprint-level, technology stack) — it is not the place for engineering-
level notes about specific classes and modules. This file tracks
concrete, code-level work that has been deliberately deferred, so it
isn't lost between sessions. Entries are removed once implemented.

---

## ParallelExecutor -- deferred, no real use case yet

Today only `SequentialExecutor(BaseExecutor)` exists. The original
version of this entry claimed `BaseExecutor`/`Stage`/
`ProcessingContext`/`Pipeline` already supported a future
`ParallelExecutor` (independent Stages via `asyncio.gather`) with no
changes needed, on the theory that Fase 1 of the ADR-010
consolidation roadmap made `ExecutionRuntime` shared and injectable
rather than tied to `SequentialExecutor` specifically. Investigated
before writing any code (per this project's own convention of
designing before implementing) -- **that premise does not hold**, for
two structural reasons found by actually reading the code, not
assumed:

1. **`Pipeline` has no stage-independence/dependency metadata.**
   `Pipeline.stages` is a plain `tuple[Stage, ...]`, ordered, with no
   graph, no groups, nothing expressing "these two are independent"
   vs "this one depends on that one's output". Running
   `asyncio.gather` over the whole tuple silently assumes every stage
   in every pipeline is always independent of every other -- an
   assumption the type system can't check and nothing prevents a
   caller from violating, producing silently-wrong results (not an
   error) if a pipeline with real inter-stage dependencies gets
   parallelized.

2. **`ExecutionRuntime` writes single, shared state slots -- not
   safe for concurrent stages.** `stage_started()`, `stage_result()`,
   `stage_failed()` write into single `ProcessingContext` keys
   (`ProcessingKeys.CURRENT_STAGE`, `STAGE_RESULT`, `EXCEPTION`), not
   a per-stage or keyed collection. Two stages running concurrently
   under `asyncio.gather`, sharing the one `ExecutionRuntime`/
   `ProcessingContext` instance `BaseExecutor.execute()` already
   creates per pipeline run today, would race to overwrite the same
   fields -- any Hook or Policy reading `CURRENT_STAGE`/`STAGE_RESULT`
   during that window could observe the wrong stage's data. This is
   the engine's central observability/policy-decision mechanism, not
   an edge case.

What *doesn't* need to change: `Executor`/`BaseExecutor._execute_pipeline()`
is a clean abstract hook a `ParallelExecutor` could plug into as-is,
and `PipelineResult` already models partial failure natively
(`successful_stages`/`failed_stages`/`has_failures` over a tuple of
`StageResult`).

Partial-failure semantics also need a decision, unresolved: today's
default `FailurePolicy(fail_fast=True)` cancels the pipeline on any
stage failure, a decision that assumed strictly sequential execution
("cancel" = "don't start the next stage"). Under concurrency this
forks -- either a failure aborts in-flight sibling stages too (risky
with real side effects like in-progress S3/DB writes, and
`asyncio.gather` doesn't cleanly support cancelling a coroutine
mid-effect), or every stage in the current parallel group always
runs to completion (`asyncio.gather(..., return_exceptions=True)`)
and "cancel" only applies to launching the *next* group.

**3 options considered:**
1. Trust the caller -- `Pipeline` stays a flat list, `ParallelExecutor`
   parallelizes everything, documented as "only use with genuinely
   independent stages"; `ExecutionRuntime` gets a lock or per-stage
   state to stop colliding. Simplest, matches the original no-Pipeline-
   change premise, but pushes correctness onto whoever assembles the
   pipeline, silently.
2. Explicit groups -- `Pipeline` gains a way to express parallel
   groups (e.g. nested tuples: a nested `tuple[Stage, ...]` = a group
   that runs in parallel, groups run in sequence). The only option
   that expresses real dependency without trusting the caller, but
   does change `Pipeline`, contradicting the original premise.
3. Don't implement it now.

**Decision: option 3, deferred.** No real use case exists inside the
processing framework today -- the concrete need that originally
motivated this (Bronze Consumer's flush bottleneck) was solved with a
plain `ThreadPoolExecutor` local to that module, outside the
processing framework entirely (see "Item 2 (parallelize flushes)
implemented" above). Revisit if a real pipeline with genuinely
independent stages shows up and the sequential cost actually matters
-- at that point, resolve gaps 1 and 2 above (option 2 is the
correctness-preferred fix for gap 1) and decide the partial-failure
semantics before writing `ParallelExecutor` itself.

## dbt-athena `s3_data_naming = schema_table` has no atomic swap on rebuild

`dbt/`'s Athena profile uses `s3_data_naming: schema_table` (fixed path
per table, `gold/{schema}/{table}/`) rather than one of the `_unique`
variants. This means a rebuild (`dbt run --full-refresh`, or any
`table` materialization) overwrites the same S3 location in place --
no atomic table-location swap, so a concurrent reader could see
inconsistent data mid-rebuild. Accepted deliberately for now: matches
the same overwrite-in-place model already used on the Spark side
(`write_delta(..., mode="overwrite")`), and nothing in this pipeline
today has a concurrent-read requirement during a rebuild window.

**Revisit if**: a concurrent consumer sensitive to mid-rebuild
inconsistency shows up -- e.g. a scheduled Power BI refresh querying
Gold while a `dbt run` is in flight. At that point, switch to
`schema_table_unique` (atomic swap, per dbt-athena's docs), accepting
its trade-off of orphaned S3 directories from old rebuilds needing
periodic cleanup.

## `src/` top-level module structure has no single source of truth

ADR-001 and ADR-004 (both dated 2026-07-19) each describe a different
`src/` module list -- ADR-001: `platform/ingestion/streaming/processing/
quality/simulator/common`; ADR-004: `platform/cloud/ingestion/streaming/
processing/quality/orchestration/analytics/common`. Neither matches the
real code: the actual top-level packages today are `common/
data_platform/ingestion/integrations/quality/simulator/streaming`
(`platform` became `data_platform`, `cloud` became `integrations`),
and that rename was never captured in an ADR.

**Not written now**: needs a new ADR reconciling the real structure
against both ADR-001 and ADR-004, not a quick edit to either -- found
while auditing all 11 ADRs for staleness, deliberately out of scope
for that pass.

## Simulator -- order status progression engine

`orders.status` has cardinality 1 today -- confirmed via a real
`SELECT DISTINCT status, count(*) FROM marketplace.orders GROUP BY
status` against Postgres: only `PENDING` exists. The generator creates
the order (and one `order_status_history` row) and never advances its
status afterward -- no `PAID`/`SHIPPED`/`DELIVERED`/`CANCELLED` exists
on any order generated so far.

This isn't "generate a new row" like the rest of the simulator already
does -- it's state change over time (e.g. an order `PENDING` for more
than N minutes becomes `PAID`, then `SHIPPED`, etc.), which needs a
temporal progression mechanism: a second, dedicated process/scheduler,
or a periodic pass that re-evaluates existing orders against
`created_at`/`updated_at` and decides whether they advance status.

**Value**:
1. Unblocks `order_status_category` as a second real business rule in
   `fact_orders` (D4) -- dropped today for lack of real variation in
   the data (confirmed while investigating D4).
2. Enriches the CDC/Kafka demonstration: a status change becomes a
   real Debezium `UPDATE` event, not just `INSERT` -- CDC has so far
   only been proven with inserts, never with an update to an existing
   row.

**Not implemented now**: recorded while investigating D4, out of scope
for that step.

## `src/` packages aren't installable -- `PYTHONPATH` required outside pytest

`pyproject.toml` has no `[build-system]` table, so `uv run python -m
simulator.app` (as documented in the README) fails with
`ModuleNotFoundError: No module named 'simulator'` -- confirmed while
re-running the simulator validation test. `uv run` only syncs
dependencies, it doesn't install the project itself, so none of
`src/`'s top-level packages (`common/data_platform/ingestion/
integrations/quality/simulator/streaming`) land in the venv's
site-packages. `pytest` doesn't hit this because
`[tool.pytest.ini_options]` separately sets `pythonpath = ["src"]`,
and `mypy`/`ruff` have their own equivalent path configs (`mypy_path`,
`tool.ruff.src`) -- three tools each independently working around the
same missing piece. Worked around for now (README) with `PYTHONPATH=src`
on the run command.

Found `src/modern_data_platform.egg-info/` already present on disk
(gitignored, dated before this investigation) -- some earlier `pip
install -e .`-style attempt was made at some point without ever adding
`[build-system]`, so it never actually linked into a venv's
site-packages.

**Fix would be**: add `[build-system]` (hatchling) +
`[tool.hatch.build.targets.wheel] packages = ["src/common", "src/
data_platform", "src/ingestion", "src/integrations", "src/quality",
"src/simulator", "src/streaming"]`, so `uv sync` installs the project
in editable mode and every `src/` package becomes importable without
`PYTHONPATH`, everywhere (`pytest`'s explicit `pythonpath` config could
then also be dropped).

**Not done now**: touches `uv.lock` (a large, tracked, shared lockfile
across a monorepo with heavy deps -- Airflow, PySpark, Databricks SDK)
for a benefit that's currently just developer convenience running the
simulator directly; also worth checking first whether the Airflow
containers' `src:/opt/mdp/src` volume mount (see
`docs/environment-inventory.md`) relies on the current flat-path
behavior before changing it.

## Fraud Detection (Sprint 15) deferred to v2

Sprint 15 in `project-decisions.md`'s Roadmap names "Fraud Detection",
but the same document's Out of Scope section excludes Machine Learning
from v1 -- and a real fraud-detection capability depends on it. Deferred
to a future v2 that includes Machine Learning; out of scope for the
current version, not started.

## Airflow remote logging is AWS-coupled by construction (accepted)

`AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER` uses the `cloudwatch://`
scheme (`CloudwatchTaskHandler`, `apache-airflow-providers-amazon`) --
the log group ARN itself is kept out of code via
`AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN` (`infrastructure/docker/.env`), but
the *mechanism* (which remote logging handler class Airflow loads) is
inherently provider-specific: S3/GCS/Azure remote logging use a
different handler and connection type entirely, not a config value
swap. There is no cloud-agnostic remote-logging abstraction in Airflow
itself to build against. If this project ever migrates away from AWS,
this handler (and the `aws_default` Connection it reads through)
would need to be replaced outright, not reconfigured. Accepted
consciously for now -- only the ARN/account/region value is kept
out of tracked files, not the provider coupling itself.

Separately, `AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN` is a value typed by
hand into `infrastructure/docker/.env`, even though Terraform already
computes this exact ARN (`module.cloudwatch_airflow.arn`,
`infrastructure/terraform/modules/monitoring/cloudwatch/outputs.tf`)
-- it just isn't exposed at the root level
(`environments/dev/outputs.tf`) or piped into
`airflow/config/terraform_outputs.json` the way `aws_region` and the
other outputs already are (see `scripts/export-terraform-outputs.sh`
and `airflow/config/bootstrap/airflow.py`). The correct long-term fix
is wiring that output through the same pipeline so this value is
derived from Terraform state instead of copy-pasted; not done here,
kept as a manually-maintained value for now.

## `airflow tasks test` does not exercise the real worker/remote-log path

`airflow tasks test <dag> <task>` runs the task inline in the CLI
process itself, not through the CeleryExecutor/worker. This matters
for anything that depends on how a *real* scheduled/triggered task
executes -- e.g. remote logging (`CloudwatchTaskHandler` is wired
through the worker's task_runner, not the `tasks test` code path): a
task that runs and logs successfully under `tasks test` proves
nothing about whether its logs actually reach CloudWatch. Confirmed
while validating Decision 3 (Airflow CloudWatch remote logging) --
`tasks test` produced no CloudWatch log stream at all, while
`airflow dags trigger` (paused immediately after, to keep the run
scoped to a single task) did. Use `dags trigger` -- not `tasks test`
-- whenever validating something that depends on the real execution
path, not just task logic correctness.

## bronze-consumer's 1024M memory limit is tight under backlog catch-up

Found live while validating Decision 4 (Prometheus + Grafana):
containerizing the Bronze Consumer for the first time made it exercise
a real historical backlog (Kafka topics never consumed before this
sprint, `mdp_bronze_consumer_lag` showed 68K-282K messages per topic)
-- the original 512M `deploy.resources.limits.memory` estimate was
sized from idle footprint, not real load, and the process hit a real
kernel cgroup OOM kill (`dmesg`: `Memory cgroup out of memory ...
anon-rss:511428kB`, right at the ceiling) while writing that backlog to
Delta. Root cause of the baseline being higher than expected:
`data_platform.bootstrap()` eagerly registers every provider (AWS,
Databricks, Airflow, Kafka) regardless of which one a caller actually
needs -- `run_bronze_consumer.py` only uses Kafka, but still pays for
`boto3`, `databricks-sdk` and the rest of that import graph.

Raised to 1024M, which held under the same catch-up load, but stayed
close to the ceiling throughout: RSS observed at ~974-1000MiB over a
15-minute window (steady, no upward trend -- ruling out a leak in that
window), i.e. 95-98% utilization the whole time. This was **not** a
no-backlog steady-state measurement -- the backlog was still draining
throughout that window (see the next entry) and never emptied, so
whether RSS would actually drop once the backlog is gone is still
unconfirmed.

**Revisit if**: this OOMs again at 1024M (raise further -- host RAM
allowing, see the swap-pressure entry below), or if the Bronze
Consumer is ever taken offline for an extended period and has to
catch up a similarly large backlog again on restart.

## Bronze Consumer's round-robin poll loop is throughput-bound, not I/O-bound

Found live while validating Decision 4, watching the real backlog
(above) drain: `mdp_bronze_consumer_lag` for `products` moved from
271312 to 271200 in 5m26s -- ~20 messages/min. At that rate, fully
draining a single topic's 68K-282K backlog is a 57-hour-to-9-day
proposition, not minutes.

Root cause, structural, not a bug: `run_bronze_consumer`'s loop calls
`provider.consume()` once per topic per iteration (a single
`Consumer.poll()`, one message), round-robin across all 16 entities,
and each buffer flush (up to `_MAX_BATCH_SIZE=100` records) serializes
a real `write_deltalake()` S3 call inline before moving to the next
entity. Throughput is capped by the sum of those per-entity S3 write
latencies per cycle, not by Kafka's own throughput or network
bandwidth -- confirmed separately that a single manual `write_deltalake()`
call completes in a few hundred ms to a few seconds.

**Fix would be**: batch-poll each topic (`consume()` returning many
messages per call instead of one) and/or flush different entities'
buffers concurrently instead of serially in the same loop iteration.

**Not done now**: out of scope for Decision 4 (observability
instrumentation, not consumer throughput) -- the metric this sprint
added (`mdp_bronze_consumer_lag`) is what makes this bottleneck visible
in Prometheus/Grafana going forward, which is the actual point; fixing
the bottleneck itself is separate follow-up work.

## Batch-poll (max_messages=25) validated: ~3x throughput, but its round-duration number isn't 1:1 comparable to the earlier 4.76s baseline

Follow-up to the entry above -- this is that entry's "batch-poll each
topic" half of the proposed fix, implemented and validated once the
memory-limit fixes (bronze-consumer 1024M -> 1536M, plus right-sizing
kafka and debezium-connect) let the container run OOM-free long enough
to observe a stable regime instead of restart noise.

**Methodology note -- the 4.76s baseline is not directly comparable to
the current round-duration mean.** Before this change, `consume()`
fetched exactly one message per topic per round (see the entry above),
so the 100-record buffer took ~100 rounds to fill and trigger a flush
-- a "flush round" (inline `write_deltalake()` calls before moving to
the next entity) was roughly 1 in 100 rounds, so almost any round
sampled at random would be a fast, flush-free one. With
`max_messages=25`, the same buffer now fills in ~4 rounds, so roughly
1 in 4 rounds includes a flush. The 4.76s baseline was most likely
(~99% probability under the old regime) a flush-free round; the
current mean -- ~21-22s, converging across 3/5/10/15-minute windows
via Prometheus `increase()` on `mdp_bronze_round_duration_seconds`,
confirmed stable (not restart transient) by checking the same query at
different offsets over a 56-minute window -- necessarily includes the
heavier flush rounds about a quarter of the time. Comparing the two
raw numbers as-is would understate the real improvement: they are not
measuring the same unit of work. Separately, it was never confirmed
whether the original 4.76s was itself a single stopwatch sample or an
average of several rounds -- not recorded at the time, so that
uncertainty stacks on top of the regime difference.

**What actually matters is throughput, not round time.** `products`
(the same topic the entry above measured at ~20 msg/min) is now at
**~61 msg/min** -- about 3x. All 14 currently-active topics sit in the
same 61-63 msg/min range, ~861 msg/min aggregate. The backlog
(58K-271K messages/topic) has not drained yet -- this is still
catch-up regime, not empty steady-state, so these numbers describe
sustained-under-backlog throughput, which is the case that matters.

**Where the bottleneck moved:** this change didn't remove the
round-robin's inline, serial `write_deltalake()` calls (the root cause
the entry above already named) -- it just shortened the period between
flushes. Roughly 1 in 4 rounds now serializes 14-16 inline S3 writes
(one per entity whose buffer crossed 100 records that round) back to
back before the loop moves on. That's a real number to size the next
fix from: **item 2 (parallelize flushes, e.g. via `ThreadPoolExecutor`)
should assume up to 14-16 simultaneous in-flight writes**, not the 2-3
originally assumed back when buffers filled far more slowly.

## Bronze Consumer's ~1.5GB memory plateau was librdkafka's prefetch buffer, not a leak or Arrow/deltalake overhead

Follow-up to the entry above: before sizing item 2's thread pool from
real headroom, the ~1.5GB plateau (RSS steady at 94-98% of the
container's 1536M limit even with batch-poll's flushes running
sequentially, no concurrency yet) needed an actual root cause, not an
assumption. Two hypotheses were ruled out with live data before the
real one was found:

- **Not a leak.** `tracemalloc.start()` plus periodic snapshots
  showed Python-tracked memory at 0.4-1.8MB against an RSS of
  ~1520-1547MB (0.0-0.1% of RSS) over a 9.5-minute window, with the
  tracked peak flat at 2.0MB for the back half of that window. No
  in-code leak.
- **Not Arrow/`deltalake` write overhead.** Once measured cleanly
  (i.e. after the real cause below was already fixed, so this
  wasn't confounded with it -- see that section's own caveat),
  per-flush RSS deltas were mostly under 6MB, 26.5MB at the observed
  max, across 40 samples spanning every active entity. Nowhere near
  1.5GB.

**Root cause, confirmed via a `stats_cb` registered on
`statistics.interval.ms` (already configured, but previously going
nowhere without a callback):** librdkafka's `queued.max.messages.kbytes`
(prefetched-message buffer per Consumer) defaults to 65536 KB (64MiB)
-- but that limit applies **per partition**, not per Consumer, and
`kafka-topics --describe` confirmed every marketplace topic has 3
partitions. The Bronze Consumer holds 16 independent Consumer
instances (one per entity, see
`KafkaMessagingProvider._resolve_consumer`), each subscribed to a
topic with a deep backlog (58K-271K messages) -- so each Consumer's
real ceiling was 3 x 64MiB = 192MB, not 64MB, and summing just 12 of
the 16 consumers' live `fetchq_size` already exceeded the entire
container's observed RSS. Worst-case theoretical ceiling across 14
active topics: 14 x 192MB = ~2.69GB -- comfortably enough to explain
an OOM under a less favorable backlog distribution than what was
actually observed.

**Fix applied:** `queued.max.messages.kbytes` set explicitly to 16384
(16MiB/partition x 3 partitions = 48MB/consumer, x 16 consumers = 768MB
worst case) in `KafkaContext.create_consumer()`. Chosen with margin: a
single 16MiB partition queue still holds ~3600 messages at the ~4.6KB/
message observed here, three orders of magnitude more than the 25
messages/topic/round the round-robin loop actually drains per pass, so
this was not expected to throttle consume_batch() -- confirmed live,
see below.

**Measured before/after, same live environment:**

| | Before (64MiB/partition default) | After (16MiB/partition) |
|---|---|---|
| RSS (steady) | ~1.50-1.56GB (94-98% of 1536M) | **754.5-764.9MB (~49-50%)** |
| Throughput/topic (`products`) | ~61 msg/min | **~107-118 msg/min** |
| Throughput aggregate (14 topics) | ~861 msg/min | **~1524.5 msg/min** |

Throughput did not just hold steady -- it **improved ~1.8x**. Likely
explanation: running at 94-98% of a cgroup memory limit was probably
already costing real performance (GC/allocator pressure close to the
ceiling) before ever risking an actual OOM kill -- relieving that
pressure seems to have helped more than the buffer-size reduction
alone would predict. Not confirmed via a separate isolated experiment
(e.g. holding the old buffer size but pinning more memory instead) --
noted as the likely explanation, not a proven one.

This is the real headroom item 2 (parallelize flushes) was waiting on
-- see that entry for the pool size derived from it.

## Item 2 (parallelize flushes) implemented: `ThreadPoolExecutor`, pool size 8, validated live

Closes out the 3-item throughput plan the two entries above are also
part of. `_flush()` (`write_deltalake()` + `commit()`) now runs on a
`_FLUSH_POOL_SIZE`-worker thread pool instead of inline in the
round-robin loop, so one entity's slow S3 write no longer blocks every
other entity's turn behind it. Concurrency is capped at one flush in
flight *per entity* (a `dict[str, Future]` in `run_bronze_consumer()`)
regardless of pool size -- both to satisfy that constraint directly
and because it's what makes the concurrency safe: an entity's
`_EntityBuffer` is only ever mutated by the main thread while that
entity has no flush in flight, and only ever read by the one worker
thread flushing it, so the two never touch it at the same time.

**Pool size (8), derived from real headroom, not a formula guess:**
idle-of-flush baseline RSS ~750MB (the previous entry's fixed
Kafka-buffer plateau), a conservative 40MB-per-concurrent-flush budget
(safety margin over the 26.5MB max observed in 40 clean post-Kafka-fix
samples), and a target ceiling of 1200MB even at full pool utilization
(~336MB/22% slack left under the container's 1536M limit) work out to
(1200-750)/40 = 11.25 concurrent flushes -- rounded down to 8.

**Validated live, same environment, sequential vs. parallel:**

| | Sequential (post-Kafka-fix) | Parallel (pool=8) |
|---|---|---|
| RSS (steady) | 754.5-764.9MB (~49-50%) | **866.2MB (56.4%)**, 670MB slack left |
| Mean round duration | ~21-22s | **~7.9-8.6s** (-2.6x) |
| Throughput/topic (`products`) | ~107-118 msg/min | **~156.2 msg/min** (+~35%) |
| Throughput aggregate | ~1524.5 msg/min | **~2203.3 msg/min** (+~44%) |

No restarts, no OOM, memory grew by the predicted amount (well inside
budget) while throughput improved further on top of the Kafka-buffer
fix's own gain. Pool size 8 needed no adjustment from this result --
there's still real headroom (670MB) if a future workload change
justifies revisiting it, but nothing here calls for that now.

**A real correctness bug found and fixed along the way, worth keeping
here since it will bite again if a future change removes the fix
without understanding why it's there:** the round-robin loop's retry
path for a still-in-flight entity used to be a bare `continue` --
correct in isolation but relying on an unstated assumption that the
main thread would incidentally yield the GIL often enough for the
worker thread executing that entity's flush to actually get scheduled
before the loop ran out of iterations. That assumption silently held
during development only because a since-removed temporary diagnostic
(a `tracemalloc` snapshot every 5 rounds) was slow enough to force
regular yields as a side effect -- once removed, a single-entity,
no-real-network-I/O scenario (exactly what
`test_batch_write_failure_leaves_offsets_uncommitted_and_retries` and
`test_batch_commit_failure_does_not_crash_and_retries_next_cycle` are)
could spin through its *entire* `max_iterations` budget faster than
the OS ever scheduled the worker thread -- confirmed reproducing
100% of the time once the loop was fast and clean, independent of how
many extra iterations of margin the test was given (tried up to
200). Fixed with an explicit `time.sleep(0)` in the busy-continue
branch, which forces a real yield instead of hoping one happens.
Production's many entities and real `consume_batch()` network calls
make this far less likely to matter there than in a tight single-
entity test loop, but "far less likely" is not "impossible" -- the
explicit yield is now unconditional, not incidental.

**Combined effect of the full 3-item plan, start to finish**
(`products` topic): ~20 msg/min (original baseline) -> ~61 msg/min
(item 3, batch-poll) -> ~107-118 msg/min (Kafka prefetch-buffer fix)
-> **~156.2 msg/min (item 2, parallel flush)** -- roughly **8x** the
original throughput, with RSS ending lower (866MB) than where item 3
alone had left it (~1.5GB), not higher.

## Host RAM stays under real pressure with the full local stack running

`free -h`, checked live while validating Decision 4 with all 16
containers up (11 pre-existing + 5 new observability services):
2.7Gi/4Gi swap in use, ~2Gi "available" out of 7.8Gi total -- even
after the `.wslconfig` fix earlier in this sprint (`memory=8GB,
swap=4GB`) resolved the original blocker. This is a host-wide symptom
that no single container's resource limit fixes -- every service
sized individually within its own conservative ceiling, but 16 of them
running simultaneously still adds up.

**Possible future action**: stop non-essential services (e.g.
`debezium-connect`, and by extension the CDC-dependent chain) when not
actively testing the streaming path, via Docker Compose profiles or
just a documented `docker compose stop <services>` command, instead of
keeping all ~16 containers up at all times during local development.
Not implemented now -- needs deciding which services are safe to stop
independently (e.g. `debezium-connect` down doesn't affect
Postgres/Kafka/batch-only work) before turning it into an actual
profile split.

**Update -- "Etapa B" complete:** every one of the 16 persistent
services now has its own `deploy.resources.limits.memory` (previously
7 did; the remaining 9 -- Airflow's 5 components, both Postgres
instances, Redis, kafka-ui -- were sized the same way as the earlier
7: live `docker stats` baseline, generous margin, applied, restarted,
re-measured). This does not resolve the host-wide symptom described
above -- summing every container's individual ceiling comes to
~13GB+, still well past the host's 8GB+4GB swap budget -- it only
means no single container can run away unbounded anymore. The
"possible future action" above is still the real fix for the
aggregate problem.

