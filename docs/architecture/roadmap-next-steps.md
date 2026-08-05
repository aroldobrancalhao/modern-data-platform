# Roadmap — Next Steps

`project-decisions.md` is frozen by its own rule (project charter,
Sprint-level, technology stack) — it is not the place for engineering-
level notes about specific classes and modules. This file tracks
concrete, code-level work that has been deliberately deferred, so it
isn't lost between sessions. Entries are removed once implemented.

---

## ParallelExecutor

Today only `SequentialExecutor(BaseExecutor)` exists. `BaseExecutor`
was already designed to be pluggable — Fase 1 of the ADR-010
consolidation roadmap made `ExecutionRuntime` shared and injectable
rather than tied to `SequentialExecutor` specifically — so a future
`ParallelExecutor` (independent Stages running via `asyncio.gather`)
should not require changes to `Stage`, `ProcessingContext` or
`Pipeline`. It has not been written or tested yet.

## StorageLocation silently mistargets trailing-slash S3 keys

`StorageLocation.__post_init__` normalizes `key` via
`PurePosixPath(key).as_posix()`, which strips trailing slashes. S3
"folder marker" objects (zero-byte keys that *do* end in `/`, e.g.
Delta's own `bronze/customers/_delta_log/_staged_commits/`) are a
distinct key from the same path without the slash. `list()` returns
the real, slash-terminated key from S3, but building a
`StorageLocation` from it (or passing it back into `delete()`) quietly
drops the slash -- so the delete request goes to a key that doesn't
exist, while the real object stays untouched, with no error raised.

Found while cleaning `bronze/customers/`, `silver/customers/` and
`gold/customers/` before a full_pipeline rerun: `S3StorageProvider.delete()`
reported success (no exception) for the `_staged_commits/` marker in
all three prefixes, but a follow-up `list()` still showed it present
every time -- confirmed via `aws s3api list-object-versions` that the
provider had been deleting `..._staged_commits` (no slash, never
existed) instead of `..._staged_commits/` (the real key). Worked
around this once via `aws s3 rm` directly on the slash-terminated key;
not fixed in code yet.

**Not corrected now**: small, isolated bug, doesn't block anything
already built -- just needs `StorageLocation` (or `S3StorageProvider`)
to preserve a trailing slash when one was present in the original key,
instead of normalizing it away.

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

