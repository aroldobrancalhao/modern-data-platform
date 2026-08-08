# Roadmap — Next Steps

`project-decisions.md` is frozen by its own rule (project charter,
Sprint-level, technology stack) — it is not the place for engineering-
level notes about specific classes and modules. This file tracks
concrete, code-level work that has been deliberately deferred, so it
isn't lost between sessions. Entries are removed once implemented.

---

## Gold CTAS tables now really land under `gold/{schema}/{table}/` -- the "no atomic swap on rebuild" risk below is live, not theoretical

This entry originally described `s3_data_naming: schema_table` as an
accepted, deliberate trade-off. It turned out to describe a
configuration that was never actually taking effect -- found while
investigating a Metabase BI Reader IAM connection (Sprint 12): Gold's
`table`-materialized models were silently landing under
`{s3_staging_dir}/tables/{uuid}/` (dbt-athena's bare fallback), not
`gold/{schema}/{table}/` at all.

**Root cause**: `mdp-athena-dev`'s `enforce_workgroup_configuration=
true` makes dbt-athena's `create_table_as.sql` macro drop the
`external_location`/computed-location clause from the generated CTAS
DDL entirely for Hive tables (`{%- if not
work_group_output_location_enforced or table_type == 'iceberg' -%}`),
regardless of `s3_data_dir`/`s3_data_naming`/`external_location`
config -- confirmed by reading the installed adapter source
(`dbt-athena==1.11.0`), not by trusting a docs summary (an earlier
attempt at this same investigation trusted a WebFetch summary claiming
`generate_s3_location()` bypassed workgroup enforcement -- it doesn't;
the macro drops the clause before that function's result is even used).

**Fix applied**: a dedicated workgroup, `mdp-athena-dbt-dev`
(Terraform: `module.athena_dbt_build`, `environments/dev/analytics.tf`
-- `modules/analytics/athena` gained an `enforce_output_location`
variable, default `true`, so `mdp-athena-dev` itself -- the one
Metabase/Power BI query against -- is untouched), with
`enforce_output_location=false`. dbt's `dbt_build` target
(`~/.dbt/profiles.yml` and `infrastructure/docker/dbt/profiles.yml`,
the latter mounted into the Airflow containers -- also found stale and
fixed) points there. `dim_customers`/`dim_products`/`fact_orders`
(`dbt/models/gold/*.sql`) each set `external_location` explicitly.
Confirmed via the real DDL (`aws athena get-query-execution`), not
just a clean exit code: `external_location='s3://.../gold/mdp_gold_dev/
fact_orders'` now genuinely appears in the `WITH (...)` clause.

**Consequence -- the original risk this entry named is now real,
not accepted-but-dormant**: before this fix, every
`dbt run --full-refresh` picked a fresh random `{uuid}` path, which
accidentally behaved like an atomic swap (old and new data never
shared a location). Now that the location is fixed
(`gold/{schema}/{table}/`), a rebuild genuinely overwrites in place
again -- the original trade-off (matching Spark's own
`mode="overwrite"`) is back in force, and unlike when this was first
written, there's now a real concurrent reader: Metabase, validated end
to end against this exact Gold layer (`POST /api/dataset` against
`fact_orders`, real data returned). The original **"Revisit if": a
concurrent consumer sensitive to mid-rebuild inconsistency shows up**
condition has been met. Not switched to `schema_table_unique` yet --
recorded here so it isn't lost, not fixed unprompted (a scheduling/
availability trade-off, not a bug, and now that `mdp-athena-dbt-dev`
is a dedicated workgroup, a bad rebuild can no longer affect anything
sharing infrastructure with the BI-facing workgroup either way).

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

## `marketplace_batch_pipeline` moved off `schedule=None` -- decision record

The DAG's own docstring named the condition for this explicitly:
"manual trigger only, until a full run has been validated end to end."
That happened this session -- a real Postgres extraction, a real
Databricks "Full Pipeline" run, and `dbt run`/`dbt test --select gold`
all green (28/28), including the Gold-location and Bronze
batch/streaming fixes above landing along the way. Moved to
`schedule=timedelta(minutes=30)`, `catchup=False` unchanged (no
retroactive runs on first deploy). No prior cron/`timedelta` precedent
existed elsewhere in `airflow/dags/` to follow -- picked `timedelta`
for a plain fixed interval over an equivalent cron string
(`*/30 * * * *`) for readability; `retry_validation.py` already
imports `timedelta` for an unrelated purpose, a mild precedent.
Unpaused and confirmed live (`airflow dags details`: `is_paused:
False`, a real computed `next_dagrun_run_after`) -- not left as a
schedule nobody actually enabled.

**Not addressed by this change**: `infrastructure/docker/dbt/
profiles.yml` (mounted into the Airflow containers) still needed its
own copy of the `mdp-athena-dbt-dev` workgroup fix from the entry
above -- found stale (still pointing at the old `mdp-athena-dev`/old
staging path) exactly because this DAG was about to start running for
real; fixed alongside it, not a separate follow-up.

## Power BI -- connection validated this session, dashboard not built

Sprint 12 (BI) picks back up here: Metabase was already done
(containerized, IAM-scoped, a real dashboard -- see the Bronze
batch/streaming and Gold CTAS-location entries above, both found and
fixed while building it). This session took Power BI from
"investigated" to **connected and validated end to end** -- Power BI
Desktop -> ODBC driver -> `mdp-athena-dev` -> Gold tables, real rows
confirmed visually in Table view for `dim_customers`, `dim_products`,
`fact_orders`. No dashboard/visual built -- deliberately out of scope
for this pass, same as the decision record above for other entries;
tracked as its own remaining-work item below.

**Reused from the earlier investigation, confirmed correct**:
- **Connection mechanism**: official AWS Athena ODBC driver + a DSN,
  no native Power BI connector for Athena. Power BI Desktop, Import
  mode (not DirectQuery -- no real need for live/scheduled data yet).
- **IAM**: `mdp-bi-reader-dev` (Terraform `module.bi_reader`), same
  identity Metabase uses, same credential pair
  (`infrastructure/docker/.env`'s `MDP_BI_READER_ACCESS_KEY_ID`/
  `SECRET`) -- reused, not regenerated.
- **Workgroup**: `mdp-athena-dev`, same as Metabase -- not
  `mdp-athena-dbt-dev`.

**New findings from actually doing the connection (Windows client,
driven interactively -- this session's environment is WSL2, so
`powershell.exe` interop scripted the installer/download but the
in-app clicks were the human's)**:

- **Power BI Desktop was already installed as a Microsoft Store
  package** (`Microsoft.MicrosoftPowerBIDesktop`, not the classic
  `.exe`/MSI from powerbi.microsoft.com) -- this turned out to matter
  (next point), not just an install-location detail.
- **Driver**: Amazon Athena ODBC 2.x, v2.2.0.1 (official download,
  `docs.aws.amazon.com/athena/latest/ug/odbc-v2-driver.html`).
  Requires local admin to install (MSI); a UAC prompt triggered from
  a non-interactive process (`powershell.exe` invoked from WSL) fails
  immediately with "operation cancelled by user" without ever
  rendering -- confirmed live, not assumed. Worked fine once the
  human double-clicked the (pre-downloaded) MSI directly.
- **DSN had to be a System DSN, not a User DSN.** Configured first as
  a User DSN (`HKCU\SOFTWARE\ODBC\ODBC.INI`) -- the driver's own
  **Test** button reported success, but Power BI's Amazon Athena
  connector still failed with `ODBC: ERROR [IM002] ... Data source
  name not found and no default driver specified`. Root cause: the
  Store-packaged Power BI Desktop runs inside an MSIX AppContainer,
  which doesn't see per-user DSNs the same way a classically-installed
  app does. Recreated the identical DSN as a **System DSN**
  (`HKLM\SOFTWARE\ODBC\ODBC.INI`, needs an elevated ODBC Data Source
  Administrator -- Task Manager's "Run new task" with the admin
  checkbox worked, where the WSL-triggered UAC path did not) and
  Power BI connected immediately. Both DSNs are named `mdp-gold-dev`;
  the User one was left in place, unused, not worth tearing down.
- **Default result fetcher hit a real driver bug against this
  workgroup.** `ResultFetcher=auto` (the default) downloads query
  results directly from S3; that path failed with `[AmazonAthena]
  [S3ClientError] ... Response checksums mismatch`. Root cause
  matches a known AWS SDK C++ issue (composite-checksum response
  validation unsupported, `aws/aws-sdk-cpp#3496`), surfaced here by
  the driver's 2.2.0.0 migration to the AWS SDK CRT HTTP client (see
  the driver's own release notes). **Fix**: `ResultFetcher=
  GetQueryResultsStream` (Advanced Options in the DSN config) --
  bypasses the direct-S3 path entirely and uses Athena's streaming API
  instead. No IAM change needed: `mdp-bi-reader-dev`'s policy already
  grants `athena:GetQueryResultsStream` (`security.tf`, added
  alongside the other Athena actions when the identity was first
  created for Metabase).
- **DSN creation could not be scripted from this session.** Claude
  Code's own auto-mode permission classifier blocked every
  `*-OdbcDsn` PowerShell cmdlet attempted via the WSL->`powershell.exe`
  bridge -- including a read-only `Get-OdbcDsn`, not just the
  registry-writing `Add-OdbcDsn`. Every DSN field in both the User and
  System DSN was entered by hand through the ODBC Data Source
  Administrator GUI. Driver installation and app-launching (
  `Start-Process`, `explorer.exe`) were not blocked -- the block was
  specific to the ODBC-DSN cmdlet family.

**Validated**: `Get Data -> Amazon Athena -> DSN mdp-gold-dev ->
Import -> dim_customers/dim_products/fact_orders -> Load`, then
confirmed in Power BI's Table view that all three tables hold real
rows (visual confirmation only -- exact row counts weren't captured
this session, no reason to expect them to differ from Metabase's
already-checked counts in `dashboards/metabase/README.md`).

**Remaining work**:
1. Build an actual dashboard/report -- this session deliberately
   stopped at connection validation, no visuals. Natural first target
   is parity with Metabase's `Gold Layer Overview`
   (`dashboards/metabase/README.md`), same underlying data, same
   caveats about the simulator's flat cardinality.
2. Decide Import vs DirectQuery only if a real need for live/scheduled
   data shows up. If scheduled refresh via Power BI Service ever
   becomes a requirement, revisit two things already flagged
   elsewhere in this file: whether an On-premises Data Gateway is
   needed, and whether `s3_data_naming: schema_table`'s "no atomic
   swap on rebuild" (see the Gold CTAS-location entry above) becomes a
   concurrency concern for Power BI the way it now genuinely is for
   Metabase.
3. Document the final setup as a new ADR (connection method, the
   System-DSN-not-User-DSN finding, the `ResultFetcher` workaround,
   auth model) once the dashboard exists -- not written speculatively
   ahead of it, same discipline as ADR-011.

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

## Bronze's batch and streaming writers shared one physical Delta table -- root cause of a real Silver duplicate-row bug, now split

Found live investigating a `unique_dim_products_product_id` test
failure (139 duplicate `product_id` rows) that surfaced once the Gold
CTAS location bug above was fixed and `dbt test` actually ran against
current data for the first time in a while. Traced layer by layer, not
assumed:

- **Postgres (source)**: clean -- `137207 = 137207` distinct
  `product_id` (`GROUP BY ... HAVING count(*) > 1` returned nothing).
  Not the simulator.
- **The duplicate pairs, compared column by column**: identical except
  `category_id` -- same `updated_at`, same Silver `processed_at`.
  Confirmed against real Postgres: the *current* `category_id` matches
  one of the two Silver rows, carrying the exact same `updated_at`
  both already had. `products.category_id` can apparently change at
  the source without `updated_at` being bumped -- an application/
  simulator gap on its own, not yet a pipeline bug.
- **Why `_remove_duplicates()` (`data_platform/processing/silver/
  transformations.py`) didn't catch it**: it isn't broken -- `dropDuplicates()`
  (all columns) only removes byte-identical rows, and these weren't
  identical.
- **Where the two versions actually came from**: `bronze/products/
  _delta_log/` was at version **2644**, `mode: Append` every ~15s --
  `bronze_consumer.py` (streaming, Kafka/Debezium, all 16 entities),
  whose own docstring already said it lands events "straight into the
  same Bronze Delta tables the batch flow writes." `ingest_sources.ipynb`
  (batch, the 7 dbt/Gold entities) writes that *same* `bronze/{entity}/`
  path with `mode="overwrite"`. Both by design, no reconciliation
  between them: a batch overwrite gives one clean snapshot; the
  streaming consumer appends real CDC events on top before the next
  Silver run reads it. Silver's own `_delta_log` (checked directly)
  confirmed a clean `Overwrite`/`REMOVE`+`ADD` per run -- the
  inconsistency was already inside Bronze by the time Silver ran.
- **Scope check**: `customers`, `orders`, `order_items`, `sellers`,
  `categories`, `payments` all showed `count(*) = count(distinct
  <key>)` -- zero duplicates. Specific to `products`, apparently the
  only one of the 7 that receives an in-place update from the
  simulator today.
- **No usable ordering signal exists to resolve this from inside
  Silver instead**: `decode_debezium_message()`/`_buffer_message()`
  (`integrations/kafka/messaging/debezium_envelope.py`,
  `bronze_consumer.py`) never extract or persist Debezium's `op`,
  `ts_ms`, or `source.lsn` -- only the business `after`/`before`
  fields reach Bronze. `updated_at` is proven unreliable (this exact
  bug). Two alternatives were considered and rejected in favor of the
  fix below: real CDC/extraction provenance timestamps (correct
  long-term, touches Bronze schema for every entity, needs a
  historical-data decision -- see Future Improvements) and ordering by
  Delta file/commit metadata (fragile -- `OPTIMIZE`/compaction can
  reorder files without changing logical recency).

**Fix applied**: `StorageConfig` (`data_platform/storage/config.py`)
gained `.bronze_batch(entity)` (`bronze_batch/{entity}`), separate
from `.bronze(entity)` (now documented as streaming-only).
`ingest_sources.ipynb`, `validate_bronze.ipynb`, `optimize_bronze.ipynb`
(the Databricks "Full Pipeline" Job) and `transform_silver.ipynb` all
read/write `.bronze_batch()` instead; `bronze_consumer.py` untouched,
still writes `.bronze()`. Validated live: real "Full Pipeline" run
(`bronze -> bronze_validate -> bronze_optimize -> silver`, 7 entities)
against the real workspace, Silver `products` back to `137207 =
137207`, `dbt run --full-refresh --target dbt_build --select gold` +
`dbt test` **28/28 passing** (was 24/28).

**Future Improvement, not urgent**: real CDC/extraction provenance
(Debezium's `source.ts_ms`, or a `PostgresExtractionStage`-stamped
`_extracted_at`) plus a generic "latest per natural key" step in
`apply_standard_transformations`, for whenever an entity legitimately
needs updates from multiple sources reconciled. Not needed today --
splitting the write paths removed the actual conflict at its root, for
every entity, not just `products`.

## `bronze_path` Airflow Variable is set but never read

`airflow/config/bootstrap/airflow.py` sets an Airflow Variable
`bronze_path: "bronze/"`, but nothing in the codebase reads it
(confirmed via a full-repo grep) -- not a functional bug today (zero
consumers means it can't silently point anyone at the wrong path), but
worth knowing before ever wiring a new consumer to it: `"bronze/"` is
the *streaming* Bronze path (see the entry above) -- a future reader
expecting this Variable to describe the batch/dbt Gold pipeline's
Bronze would get the wrong one. Not fixed now -- no real consumer to
fix a value for yet.

## Airflow's AWS credentials in `infrastructure/docker/.env` are a personal-key copy, not scoped

`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in `infrastructure/docker/.env`
(used by the Airflow `aws_default` Connection) are, per the comment
already on those lines, a direct copy of the `~/.aws/credentials
[default]` profile (`terraform-admin` -- confirmed via `aws sts
get-caller-identity`) -- the same full-access key used for every
manual `aws`/`dbt` command on this machine, not an identity scoped to
what Airflow's DAG tasks actually touch (Postgres extraction to S3,
Glue registration).

Found while investigating IAM for the BI Reader identity (Sprint 12,
Metabase/Power BI): `mdp-bi-reader-dev` (`module.bi_reader`,
`environments/dev/security.tf`) is the first credential in this
project scoped to only what its consumer needs (Athena workgroup +
`mdp_gold_dev` + `gold/`/`athena/` S3 prefixes) -- Airflow's own
credential predates that pattern and was never revisited against it.

**Not fixed now**: out of scope for the BI integration work that
surfaced it. Fixing it means defining what Airflow's tasks actually
need (S3 `bronze/`/`silver/`/`checkpoints/`, Glue bronze/silver
registration -- not gold, not IAM/Terraform-admin actions), creating a
dedicated IAM User (or role, if Airflow ever runs on infrastructure
that can assume one) scoped to exactly that, then rotating
`infrastructure/docker/.env` to the new key.

**Revisit**: next time IAM/credentials in this project get touched, or
before this project's AWS usage moves beyond a single local dev
machine.

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

