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

## Kafka consumer loop (real streaming)

`MessagingProvider`, `KafkaMessagingProvider` and
`MessagingContextWriter` exist and are tested against the real local
Kafka broker (Fases M1–M3), proving a Stage can consume one message
and publish it into the `ProcessingContext`. The continuous loop that
listens to a topic and triggers a Pipeline per message (the "Bronze
Consumer" of the streaming flow described in ADR-0008) does not exist
yet. It also depends on the simulator actually running, so there is
real business data flowing through the Debezium topics to consume.

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
