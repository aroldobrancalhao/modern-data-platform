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

## Airflow's AWS credentials -- partially scoped this session, dbt still on the personal key

**Update, 2026-08-10, later the same session**: `bronze-consumer`'s own
credential swap (mentioned as separate, uninvestigated remaining work
below) is done -- a dedicated `mdp-bronze-consumer-dev` IAM User
(Terraform `module.bronze_consumer`) replaces the personal key in
`docker-compose.yml`, applied and confirmed live (S3 writes to
`bronze/` succeeding continuously on the new identity). Only
`dbt_run_gold`/`dbt_test_gold` (below) is still on the personal key.
This entry's title and "Remaining work" section below are otherwise
kept as originally written; only the bronze-consumer status changed.

`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in `infrastructure/docker/.env`
used to be a direct copy of the `~/.aws/credentials [default]` profile
(`terraform-admin`) -- the same full-access key used for every manual
`aws`/`dbt` command on this machine, not an identity scoped to what
Airflow's DAG tasks actually touch. Investigated for real this
session (read `marketplace_batch_pipeline.py`, `postgres_extraction_
stage.py`, `dbt/profiles.yml`, `aws_context.py` -- not assumed) rather
than picking up the "S3 bronze/silver, Glue bronze/silver" scope this
entry originally guessed at.

**What Airflow's own credential actually does, confirmed live**:
1. `extract_postgres` -- S3 `raw/` read/write/list/delete (7
   entities), via `AwsContext`'s boto3 default-credential-chain
   (no Connection object involved).
2. CloudWatch remote task logging -- via the `aws_default` Connection,
   `AirflowManager._build_connections`.
3. `dbt_run_gold`/`dbt_test_gold` (`BashOperator`, real `dbt` CLI) --
   needs real write access to Athena (`mdp-athena-dbt-dev` workgroup),
   Glue (read `mdp_silver_dev`, write `mdp_gold_dev`), and S3 (read
   `silver/`, write `gold/`) to build Gold -- `dbt/models/gold/*.sql`
   `ref()` the `stg_*` Silver models directly, so this is a real
   dependency, not a guess.

**Fixed this session (Terraform `module.airflow_ingest`,
`environments/dev/security.tf`)**: a dedicated IAM User,
`mdp-airflow-ingest-dev`, scoped to exactly items 1-2 above -- S3
`raw/*` read-write-list-delete, and `CreateLogGroup`/`CreateLogStream`/
`DescribeLogStreams`/`PutLogEvents`/`GetLogEvents` on the Airflow
CloudWatch log group only. **Deliberately excludes item 3** (dbt) --
covering it would have made this identity nearly as broad as the
personal key it replaces, a real architectural discussion (see
"remaining work" below), not something to decide unilaterally mid-fix.

`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (the generic, boto3-default
env var names) now hold `mdp-airflow-ingest-dev`. The personal key is
kept under its own name, `MDP_PERSONAL_ACCESS_KEY_ID`/
`MDP_PERSONAL_SECRET_ACCESS_KEY`, and reaches the two things that
still need it explicitly:
- `dbt_run_gold`/`dbt_test_gold`: `BashOperator(env=DBT_AWS_
  CREDENTIALS, append_env=True)` in `marketplace_batch_pipeline.py` --
  `append_env=True` merges rather than replaces the subprocess
  environment, so only these two vars are overridden.
- `bronze-consumer` (`docker-compose.yml`): a separate container, own
  write path (`bronze/`, unrelated to `raw/`) -- its compose block now
  points at `MDP_PERSONAL_ACCESS_KEY_ID`/`SECRET` explicitly instead of
  inheriting the generic names, so the split above didn't silently
  change its credential.

**A real incident found and fixed live, not assumed away**: the first
IAM policy version omitted `logs:CreateLogGroup` (reasoned the log
group already exists via Terraform, so it shouldn't be needed) --
Airflow's CloudWatch handler (`watchtower`) calls `CreateLogGroup`
defensively before creating a log stream regardless, and IAM denies
the action before any "already exists" check runs. This crash-looped
the entire `dag-processor` job (not just remote logging), which is why
a DAG run sat in `queued` with zero tasks scheduled for several
minutes after the credential rotation -- confirmed via
`dag-processor` container logs, not assumed to be a parsing delay.
Fixed by adding the action to the policy (a second, minimal
Terraform apply).

**Validated end to end**: triggered `marketplace_batch_pipeline`
manually after the fix -- `extract_postgres` succeeded on
`mdp-airflow-ingest-dev`, CloudWatch remote logging succeeded (no more
`AccessDeniedException`), and `dbt_run_gold`/`dbt_test_gold` succeeded
on the personal key via the `BashOperator` override. The concurrently-
firing scheduled run (30-min cadence) succeeded too, and
`bronze-consumer` stayed healthy throughout -- confirmed the
`MDP_PERSONAL_*` rename didn't silently break it.

**Remaining work**: `dbt_run_gold`/`dbt_test_gold` and
`bronze-consumer` are still on the personal `terraform-admin` key.
Scoping dbt's own identity is a bigger question than the
`mdp-airflow-ingest-dev` split -- it would need Athena
(`mdp-athena-dbt-dev`), Glue read on `mdp_silver_dev`, Glue write on
`mdp_gold_dev`, and S3 read `silver/`/write `gold/`, i.e. close to
everything dbt itself needs to build Gold. `bronze-consumer` needs its
own separate investigation (S3 `bronze/` write, its own Kafka/Debezium
CDC path) -- not covered here at all.

## Databricks pipeline stages were spending most of their time on `%pip install`, not data processing -- fixed

Investigated why `run_databricks_full_pipeline` took ~13-14 minutes
for a ~137k-row dataset. **Not cluster cold-start** (ruled out with
real numbers, not assumed): a clean, non-queued historical run showed
`queue_duration: None` and `setup_duration: 4000` (4 seconds) via the
Databricks Jobs API (`GET /api/2.1/jobs/runs/get`) -- the ~13-14
minutes were entirely inside each stage's `execution_duration`
(bronze 198s, bronze_validate 141s, bronze_optimize 169s, silver
215s).

**Real cause, confirmed by reading the notebooks and the wheel build,
not guessed**: all 4 notebooks (`notebooks/bronze/ingest_sources.
ipynb`, `validate_bronze.ipynb`, `optimize_bronze.ipynb`, `notebooks/
silver/transform_silver.ipynb`) ran `%pip install $wheel_glob` +
`dbutils.library.restartPython()` on every single execution -- and
the wheel being installed (`uv build --wheel`, no scoping) pulled in
`[project.dependencies]`'s *entire* list, including `apache-airflow==
3.3.0` (one of the largest dependency trees in the Python ecosystem),
`apache-airflow-providers-standard`, `dbt-athena`, `dbt-core`,
`confluent-kafka` -- none of which any of the 4 notebooks import
(checked their actual `import` lines: only `data_platform.compute.*`/
`storage.config`, needing `pydantic` and Databricks-Runtime-provided
`pyspark`).

**Fixed, two complementary changes**:

1. **Scoped the wheel** (`pyproject.toml`): moved
   `apache-airflow`/`apache-airflow-providers-standard` (`orchestration`),
   `dbt-athena`/`dbt-core` (`warehouse`), and `confluent-kafka`
   (`streaming`) into `[project.optional-dependencies]`. `uv build
   --wheel` only bakes `[project.dependencies]` into the wheel's
   `Requires-Dist` -- confirmed by inspecting the built wheel's
   `METADATA` directly, not assumed. Local dev needs everything: README
   now says `uv sync --all-extras`. `infrastructure/docker/streaming/
   Dockerfile` (bronze-consumer, needs `confluent-kafka`) now passes
   `--extra streaming` explicitly. `airflow/Dockerfile` installs
   Airflow/dbt itself already (hardcoded, not derived from this file --
   see that file's own comment), so it's unaffected.

2. **Removed the per-notebook `%pip install`/`restartPython()` cell
   entirely**, replaced with a Databricks workspace base environment
   (`mdp-bronze-silver`, `workspace-base-environments/
   mdp-bronze-silver-13015gfsq6`) referenced from each `*_job.yml`'s
   `environments`/`environment_key` -- dependencies are pre-materialized
   once, not reinstalled on every run.

**A real, live-caught bug in the base environment's own dependency
list**: the first attempt pinned `delta-spark>=4.3.1`, which failed --
`ERROR: Cannot install delta-spark>=4.3.1 ... The user requested
(constraint) delta-spark==3.4.0` -- the Databricks Runtime locks
`delta-spark` (and `pyspark`) via its own immutable package
constraints; declaring a version at all, let alone a newer one,
conflicts with the runtime's pin. Fixed by not declaring
`delta-spark`/`pyspark` in the environment spec at all (same as
`pyspark`, which was already "Requirement already satisfied" even
before this fix) -- confirmed via the Environments API's own
materialization log, not assumed fixed after editing the YAML.

**Revisited, not just left as a side effect**: checked afterward
whether `pyspark` belonged in the scoped dependency list at all, or
was only there because `configure_spark_with_delta_pip()` imports it
(`data_platform/compute/spark.py`) -- not because the *environment*
needs to install it. Official docs (`docs.databricks.com/aws/en/
compute/serverless/dependencies`) settle it: *"Do not install PySpark
or any library that installs PySpark as a dependency on your
serverless notebooks. Doing so will stop your session and result in
an error."* -- Databricks Runtime provides `pyspark` (and, per the
fix above, `delta-spark`) natively; declaring either isn't just
redundant, it's actively unsafe. The validated run (next section)
already exercises exactly this -- neither package declared anywhere
(wheel or environment spec), both notebooks' `import pyspark.sql`/
`from delta import configure_spark_with_delta_pip` succeeded -- so
this is confirmed by a real passing run, not just the doc quote.

**No manual UI step needed -- found live, contradicting an earlier
web-search-sourced assumption in this same investigation**: the
`databricks-sdk` package's own docstrings (introspected locally, not
trusted from public docs search results, which had claimed
`environment_key` doesn't apply to notebook tasks) state plainly: *"For
serverless notebook tasks, if the environment_key is not specified,
the notebook environment will be used if present. If a jobs
environment is specified, it will override the notebook environment."*
Wiring the environment via `environment_key` in the bundle YAML (done)
is therefore fully declarative -- no per-notebook Environment side
panel click needed, unlike the original plan for this investigation.

**Two trade-offs accepted, not silently absorbed**:
- **Portability loss**: `base_environment: workspace-base-environments/
  mdp-bronze-silver-13015gfsq6` is tied to this one real deployment
  (the resource ID is workspace-specific) -- the old `wheel_path`
  parameter (`${workspace.root_path}/artifacts/.internal`, now removed)
  was deliberately portable across users/targets (dev/prod). Only one
  target is actually in use today, so this is acceptable now, but
  **revisit if/when a second real target (e.g. `prod`) gets stood up**
  -- the base environment would need creating there too, with its own
  ID substituted into all 4 `*_job.yml` files.
- **Stale-cache risk**: the wheel's filename is static
  (`modern_data_platform-0.1.0-py3-none-any.whl` -- `pyproject.toml`'s
  version isn't bumped per deploy) and the base environment references
  it by that exact path. Confirmed live that this isn't hypothetical:
  the first `databricks bundle deploy` after the wheel-scoping change
  did **not** get picked up until a manual `refresh-workspace-
  base-environment` call -- the environment had already materialized
  against the *old*, unscoped wheel moments earlier and kept serving
  that cached result. **Not fixed now**: the real fix is versioning the
  wheel's filename per deploy (e.g. a commit-hash suffix) and calling
  `refresh-workspace-base-environment` as part of the deploy step --
  out of scope for this pass, tracked here so it isn't lost.

**Validation pending**: measure real per-stage timing on the next
`marketplace_batch_pipeline` run against the new setup (via the same
`GET /api/2.1/jobs/runs/get` approach used for the baseline above) and
compare against the 198s/141s/169s/215s baseline; re-run `dbt test
--select gold` to confirm 28/28 still passes.

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

**Update, 2026-08-10**: this aggregate pressure is exactly why a
drafted `mdp-kafka` memory-limit increase (see "Kafka broker was
OOM-killed today", further down this file) was deliberately *not*
applied this session -- `free -h` checked live again, essentially
unchanged from the numbers above (~262MiB free, swap ~62% in use).
That entry's diff stays as a candidate for whenever this entry's
"possible future action" is actually tackled, not as a standalone
point fix.

## Bronze Consumer's commit-failure retry can livelock an entity permanently -- found live during the Frente 3 full reprocess, fixed later the same session

**Update, 2026-08-10, later the same session**: fixed --
`recover_from_lost_assignment()` (`KafkaMessagingProvider`, called from
`_flush()`'s exception handler in `bronze_consumer.py`) discards and
recreates the stuck consumer specifically on `_ASSIGNMENT_LOST`,
clearing the buffer that was keeping `remaining > 0` shut. Both
follow-ups from the "deliberately deferred" section below are done:
item 1 (the livelock itself) via that fix; item 2 (duplicate rows
already written) confirmed as no action needed -- see "Frente 3 (CDC
provenance) close-out" further down this file, `_deduplicate_by_key`
validated against real data. Regression test:
`test_recovers_and_resumes_consuming_after_an_assignment_lost_commit_failure`
(`tests/unit/streaming/consumers/test_bronze_consumer.py`) -- confirmed
failing without the fix, passing with it. The findings below are kept
as-is (real, live investigation notes), not rewritten after the fact.

**Found while monitoring the Frente 3 CDC-provenance reprocess's**
drain: 8 of the 16 entities (`payments`, `inventory_movements`,
`order_status_history`, `reviews`, `shipments`, `products`, `orders`,
`warehouses`) stopped making any progress at all -- not slow, *frozen*,
while the other 8 kept draining normally. `mdp_bronze_consumer_lag`
looked identical across two 30-minute checks for the frozen set, which
is what surfaced it.

**Mechanism, traced through the real code and confirmed live:**
1. `_flush()`'s existing (pre-existing, predates this session) design
   deliberately does *not* clear an entity's buffer when
   `provider.commit()` fails (only `write_deltalake()` failing is
   handled the same way) -- so the exact same buffered records retry
   next cycle. Correct and intended for the ordinary case (write
   landed, commit didn't).
2. `run_bronze_consumer()`'s round-robin loop only calls
   `provider.consume_batch()` (-> `Consumer.consume()`, the *only*
   call that lets `confluent-kafka`/librdkafka actually process a
   revoked-and-rejoin group-membership callback) when the entity's
   buffer has room: `remaining = min(_MAX_BATCH_SIZE -
   len(buffer.records), _MAX_POLL_BATCH_SIZE)`, gated by `if remaining
   > 0`.
3. Once a commit fails with `KafkaException{code=_ASSIGNMENT_LOST}`
   (partition assignment revoked -- plausible and apparently common
   under this reprocess's load: 16 entities' consumers, an 8-worker
   flush pool, real queuing delays under a multi-million-message
   backlog) **while the buffer happens to be exactly full**
   (`_MAX_BATCH_SIZE`), `remaining` is permanently `0` from that point
   on. `consume_batch()` -- the only thing that could let the consumer
   rejoin the group -- is never called again for that entity. The
   commit can therefore never succeed again, and the buffer can never
   drop below full, either: a closed loop with no exit.
4. Net effect confirmed live for `products` (container uptime
   ~1h25min at the time of the check): **519 failed-flush cycles**,
   **0** successful ones, real Postgres source `137,207` rows, but the
   real Bronze Delta table already had **57,800 total rows for only
   5,200 distinct `product_id`** -- `write_deltalake()` was
   succeeding every cycle (only `commit()` was failing), so the same
   small, stuck window of records was being re-appended as genuine
   duplicates, dozens of times per minute, indefinitely -- not merely
   idle.

**Why this hasn't been seen before**: the retry design's own docstring
already documents having seen `_ASSIGNMENT_LOST` live, as an accepted,
presumed-transient edge case. It likely always *was* transient before
-- a full buffer recovering within a round or two, before this reprocess
put 16 entities' consumers and an 8-worker flush pool under sustained
load extreme enough (a multi-million-message full-history catch-up,
not steady-state trickle CDC) to turn a rare blip into a permanent,
self-sustaining livelock for over half the entities at once.

**Not this session's `_cdc_ts_ms` change** -- `_flush()`'s buffer/retry
design and the round-robin loop's `remaining > 0` gate are both
untouched by that diff; this is a correctness gap in code that
predates it, only now exposed by exactly the kind of extreme backlog
this reprocess intentionally created.

**Remediated for now, root cause NOT fixed**: `docker restart
mdp-bronze-consumer` -- confirmed live afterward that all 16 partitions
rejoined the group and, specifically for the previously-stuck
`products`, that its committed offset was genuinely advancing again
(two `kafka-consumer-groups --describe` checks 25s apart, offset moved
forward on 2 of 3 partitions) and that writes were succeeding again
across all 16 entities, not just the previously-healthy 8. This clears
the immediate blockage but does **not** fix the underlying bug -- the
exact same load pattern could livelock the same or a different subset
of entities again, and there's no automatic recovery if it does.

**Two follow-ups this surfaces, both deliberately deferred, not
implemented now:**
1. **The livelock itself**: `_flush()`/the round-robin loop needs a
   way to guarantee forward progress on a `_ASSIGNMENT_LOST` (or any
   commit failure) even with a full buffer -- e.g. always calling
   `consume_batch()` regardless of `remaining` (accepting the
   over-`_MAX_BATCH_SIZE` risk this constant exists to avoid, or
   handling it separately), or capping consecutive commit-failure
   retries for an entity before forcing that entity's cached
   `Consumer` to be discarded and recreated from scratch.
2. **Duplicate rows already written**: the 8 affected entities' Bronze
   Delta tables likely still contain meaningfully more duplicate rows
   than the other 8 (only `products` was actually measured: ~11x
   duplication on a ~5.2k-row stuck window) from the hours they spent
   livelocked before the restart. Bronze already tolerates multiple
   versions of the same row by design (`_deduplicate_by_key` exists
   for exactly this in Silver), so this isn't a correctness problem
   for any real consumer today (there still isn't one -- see the
   entry above), just extra storage/scan cost sitting in these 8
   tables until they're rebuilt or cleaned up.

## Kafka broker was OOM-killed today, triggering the 2026-08-10 resume's disruption -- found, not fixed

Found while diagnosing why a plain `docker restart mdp-bronze-consumer`
(the resume session's first, reflexive remediation attempt) didn't
cleanly restore throughput the way the original livelock entry's own
remediation note predicted. Traced instead of assumed:

- `mdp-kafka`'s container (`docker inspect .State.StartedAt`) had
  actually restarted **today**, mid-session, independent of anything
  this session did to it -- `2026-08-10T11:39:22Z`, while
  `mdp-bronze-consumer` had been running continuously since
  `2026-08-10T10:48:29Z` (no restart). Broker logs confirm a real
  restart, not a network blip: `BrokerLifecycleManager` heartbeat
  failures starting `11:34:41Z`, then a clean `Kafka Server started`
  at `11:41:29Z`.
- `dmesg` confirms the mechanism directly, not by inference: a real
  cgroup OOM-kill of the broker's own `java` process --
  `Memory cgroup out of memory: Killed process ... (java) ...
  oom_memcg=.../850471351cb6...` -- `850471351cb6` is `mdp-kafka`'s
  own container ID (confirmed via `docker stats`), not a different
  service. `mdp-kafka`'s memory limit is `768MiB`
  (`infrastructure/docker/docker-compose.yml`); live usage immediately
  after the restart was already back up to `528MiB` (~69%), i.e.
  little headroom under the load this reprocess generates.
- Consequence for the consumer group: the broker restart forced every
  one of `bronze-consumer`'s 16 per-entity `Consumer` instances to
  rejoin the group at once (not just the ones already stuck in the
  pre-existing livelock), which is why the resume session's `docker
  restart mdp-bronze-consumer` produced a *worse*-looking initial
  state (a `kafka-consumer-groups --describe` briefly reporting **no
  active members at all**, zero successful flushes across all 16
  entities for several minutes) than the original livelock entry's own
  "restart cleared it in under a minute" experience -- that entry's
  remediation was tested against a livelock with a *healthy* broker
  underneath it; this time the broker itself needed to recover too.

**Not fixed here**: raising `mdp-kafka`'s memory limit (mirroring the
same live-measure-then-raise approach already used for
`bronze-consumer` -- see "bronze-consumer's 1024M memory limit is
tight under backlog catch-up" earlier in this file) is the obvious
candidate fix, but wasn't sized or applied this session -- found and
recorded as a real, evidenced root cause, not acted on unilaterally on
live infra mid-reprocess.

**Update -- a diff was drafted (768M -> 1024M,
`infrastructure/docker/docker-compose.yml`'s `kafka` service,
comment documents the reasoning and the trade-off in full), but a
conscious decision was made not to apply it this session, and not to
bundle it into Frente 3's close-out restart either.** Checked before
deciding, not assumed: real host headroom right now (`free -h`) is
~262MiB truly free, ~2.5GiB "available", swap already at ~3.7GiB/6GiB
(62%) -- the same tight-host condition the "Host RAM stays under real
pressure" entry below already names as still open. Raising this one
container's ceiling doesn't create new host RAM; it just lets Kafka
claim more of an already-oversubscribed shared pool, which could
surface as swap thrashing or the kernel's host-level OOM killer
picking a *different* victim instead (this session's own `dmesg`
capture from the original OOM event window already shows exactly that
-- `airflow` processes killed in the same window, not just
`mdp-kafka`). No urgency justified deciding this mid-reprocess either:
the broker has stayed healthy for ~5h since the one restart, with no
recurrence. Left as a real, still-open candidate -- but for a session
that deliberately tackles the *aggregate* host memory pressure (e.g.
the Compose-profile idea already recorded below, stopping
non-essential services), not as a point fix to one container's limit
picked in isolation.

**Update, 2026-08-10 (later the same day)**: the drafted diff no
longer lives in `docker-compose.yml`'s working tree -- see
"`docker-compose.yml`'s working tree isn't just a staging area, it's
what Compose reconciles live infra against" below for why, and
`docs/architecture/deferred-patches/kafka-memory-limit-768-to-1024.patch`
for the diff itself (unapplied, `git apply` when this is actually
decided).

## `docker restart mdp-bronze-consumer` failed outright: container process was a zombie -- `--init` missing from the compose service, fixed later the same session

**Update, 2026-08-10, later the same session**: fixed -- `init: true`
added to the `bronze-consumer` service (`infrastructure/docker/
docker-compose.yml`, commit bundled with the round-robin tuning +
credential swap restart), confirmed live afterward via `docker inspect
mdp-bronze-consumer --format '{{.HostConfig.Init}}'` returning `true`.
The "Not fixed here" section below is kept as-is (the real reasoning
for not applying it in that earlier moment), not rewritten after the
fact.

Found live during the 2026-08-10 resume session's first remediation
attempt: `docker restart mdp-bronze-consumer` returned an error
instead of restarting --
`Cannot restart container ...: container ... PID ... is zombie and
can not be killed. Use the --init option when creating containers to
run an init inside the container that forwards signals and reaps
processes`. Docker eventually forced the container to exit (`137`,
i.e. `SIGKILL`) after its own internal retry/timeout, but it then sat
**stopped** rather than coming back on its own -- `restart:
unless-stopped` (`infrastructure/docker/docker-compose.yml`) does not
cover this path, since the container wasn't "stopped" through that
policy's own mechanism. A plain `docker start mdp-bronze-consumer` was
needed to bring it back up manually.

**Root cause, per Docker's own error message**: the `bronze-consumer`
service in `infrastructure/docker/docker-compose.yml` has no `init:
true` (or equivalent `--init`), so PID 1 inside the container is the
Python process itself rather than a real init (e.g. `tini`, which
Docker's `--init` flag wires in automatically) -- without one, PID 1
never reaps zombie child processes, and a signal sent to PID 1 that it
doesn't handle itself has nothing forwarding it appropriately either.
Not confirmed which specific child process this session's zombie was
(not investigated further -- out of scope for a resume session focused
on the reprocess itself).

**Not fixed here**: adding `init: true` to the `bronze-consumer`
service (Compose's native, one-line equivalent of `docker run --init`)
is the obvious fix and low-risk, but wasn't applied to
`infrastructure/docker/docker-compose.yml` this session -- found and
recorded, not changed on live infra mid-reprocess without a separate,
explicit go-ahead.

## `docker restart` on `bronze-consumer` silently keeps running the old code -- a plain restart is not a deploy for this service

Found while applying the livelock fix (two entries above) this same
session: `bronze-consumer`'s image (`infrastructure/docker/streaming/
Dockerfile`) `COPY`s `src/` in at *build* time -- unlike Airflow's
containers, which mount `src:/opt/mdp/src` live (see
`docs/environment-inventory.md`) -- so there is no volume carrying
source changes into the running container.
`docker restart mdp-bronze-consumer` (or the container recovering on
its own via `restart: unless-stopped`) reruns the exact same image,
i.e. the exact same code that was already running, silently -- no
error, no warning, a healthy container, just still the old binary.
The correct deploy sequence for any `src/` change is `docker compose
build bronze-consumer && docker compose up -d bronze-consumer`
(rebuild, then recreate), not a bare restart -- confirmed live this
session: the livelock fix only took effect once done this way.

**Update -- confirmed, not just assumed**: applies to swapping
`bronze-consumer`'s AWS credential now that `mdp-bronze-consumer-dev`
(dedicated IAM, see the next entry) is applied. Re-read
`docker-compose.yml`'s `bronze-consumer` block specifically for this:
it's an environment-variable change only (the `AWS_ACCESS_KEY_ID`/
`AWS_SECRET_ACCESS_KEY` lines), matching the existing `AWS_REGION`/
`AWS_DEFAULT_REGION` precedent already in that same block ("no image
rebuild needed since it's config-only") -- **recreate only**
(`docker compose up -d bronze-consumer`), no `build` needed. The
compose diff itself (pointing at `MDP_BRONZE_CONSUMER_ACCESS_KEY_ID`/
`SECRET` instead of `MDP_PERSONAL_*`) and the matching
`.env.example` entry are both written and ready -- deliberately
**not rolled out yet** (`MDP_BRONZE_CONSUMER_*` left blank in the real
`.env`, container still running on the personal key): the container
already restarted twice today (one of them the zombie-PID incident
above), and the decision was to bundle this credential swap into
Frente 3's close-out restart instead of a third one now without a real
need -- see that section's own entry for status.

## `test_bronze_consumer_real_kafka.py`'s stale-topic-assumption bug -- fixed (spin-wait tax)

First flagged as an "explicitly left out of scope" finding during the
Frente 3 CDC-provenance work (this test's own `carriers`-topic-is-
near-empty docstring assumption was already stale then). Investigated
for real this session (ran the test live, repeatedly, against real
Kafka/Postgres/Debezium -- not assumed from reading the code).

**Root cause, confirmed live, not the originally-guessed one**: it's
not really "the topic got too big for a 30-iteration budget" (though
the topic *is* permanently growing -- every run leaves 2 Kafka messages
behind forever, Postgres cleanup doesn't touch Kafka). The real cost is
structural: with `_MAX_BATCH_SIZE` patched to 1, `run_bronze_consumer`'s
round-robin loop spends nearly its entire iteration budget in its own
busy-wait branch (`time.sleep(0); continue`, taken while the one single
message's flush -- including a real network `commit()` -- is still in
flight on a worker thread), not actually polling. Measured directly
with a `time.sleep` call-counter: **29 of 30 iterations were pure
spin-wait for a single message**. This is exactly the risk this same
loop's own code comment already named (see "Item 2 (parallelize
flushes) implemented" above, the `time.sleep(0)` fix and its comment
about "a tight single-entity test loop") -- confirmed here as a real
instance of it, in a different test than the one that comment was
originally about.

**Fixed**: `_MAX_BATCH_SIZE` raised to match production's own
`_MAX_POLL_BATCH_SIZE` (25, not 1) -- far fewer flush cycles, far less
spin-wait tax paid overall. `_MAX_BATCH_AGE_SECONDS` patched down to
3.0s (from production's 30s) so a trailing partial batch (whatever
doesn't divide evenly into 25) still flushes promptly instead of
sitting for a real 30s. `_MAX_POLL_ITERATIONS` raised 30 -> 500 for
headroom against the topic's permanent growth. This part is done --
before this fix, the test failed 100% of the time (0/8+ live runs),
every time stalling after exactly one message. See the next entry for
what's still open.

## `run_bronze_consumer` sometimes doesn't find messages that are genuinely sitting in the topic -- symptom documented, root cause NOT found, own-noise hypothesis tested and weakened

Found live while validating the fix above, in the same session -- kept
as its own entry (not just a footnote on that fix) because it's a
different, still-open question: **does `run_bronze_consumer` itself
have a real bug**, separate from anything the fix above touched.

**Symptom**: after the spin-wait fix, the test passes most of the time
but not reliably -- **roughly 60-70% across 10+ consecutive live runs**
this session. Every failure has the same shape: `run_bronze_consumer`
stops finding further messages part-way through, short of the topic's
real total, and never resumes within its iteration budget. Confirmed
this isn't "the message never arrived" -- for a failed run, the
"missing" messages (including the test's own inserted row) were
independently verified still genuinely present in the topic afterward,
via a separate plain `Consumer.consume()` script pointed at the same
topic. Debezium's own produce latency was also measured directly
(seek-to-tail, then insert: a consistent ~0.2s) and ruled out -- far
too fast to explain the gap.

**What's been ruled OUT, not just suspected**: every raw,
single-threaded reproduction of the same consume-then-commit pattern
(same client config, same batch size, committing after every batch, in
a plain loop with no `run_bronze_consumer` involved) drained its topic
completely and reliably, repeatedly. Only `run_bronze_consumer`'s real
control flow -- `consume_batch()` on the main thread, `write_deltalake()`
+ `commit()` on a worker thread via `ThreadPoolExecutor`, gated by the
`in_flight` per-entity tracking -- ever showed the gap, and not on any
fixed pattern (different attempt counts, different total messages
written each time it happened).

**Hypothesis tested this session, weakened by the result -- own
test-battery noise (many back-to-back real-Kafka runs, each spinning
up and abandoning a fresh consumer group against the same broker
within seconds of the last, causing broker-side rebalance churn
distinct from normal usage)**: checked by re-running the same battery
with one **fixed** consumer group reused across every run instead of a
fresh one each time -- if the gap were purely this session's own rapid
group churn, consolidating to one group should have reduced or removed
it. It didn't: the fixed-group runs were **not better, and looked
worse** (multiple runs hung/timed out rather than failing cleanly,
across two separate batches of ~5 attempts each). This doesn't prove
the noise hypothesis wrong (the sample is small, and a single
long-lived group being hammered by rapid rejoin/leave cycles from
repeated pytest invocations is its own kind of load, not a clean
control), but it does not support it either, and reusing a group made
an already-intermittent symptom look less predictable, not more
stable -- worth knowing before anyone re-reaches for "just use one
group" as the fix.

**Explicitly checked and ruled out: this is not the same mechanism as
the Bronze Consumer livelock fix from earlier in this same session
(`MessagingProvider.recover_from_lost_assignment()`, triggered on
Kafka's `_ASSIGNMENT_LOST`).** The second fixed-group-id batch (5 runs,
full `-v -s` output captured and kept, not just a pass/fail tally)
was grepped directly for that mechanism's own log line ("lost its
Kafka group assignment"), the raw `_ASSIGNMENT_LOST`/`NOT_COORDINATOR`
error codes, and any `error`/`warning`-level log line at all: **zero
matches across all 5 runs**, including the one that failed cleanly and
the four that hung. Whatever stalls `run_bronze_consumer` here, it is
not going through a caught commit-failure exception at all (the
existing `except Exception` in `_flush()` would have logged
*something* -- either the new WARNING or the old "flush failed"
error) -- `consume_batch()` itself is just returning nothing, silently,
which is consistent with the "distinct failure mode" framing above and
rules out "it's actually today's fix's own bug/edge case" as an
explanation.

**What's needed to actually distinguish self-inflicted load from a
real `run_bronze_consumer` bug, not done yet**:
1. Run the test in true isolation -- a single invocation, by itself,
   with real idle time before and after (not back-to-back with
   anything else touching Kafka), repeated on separate occasions (e.g.
   once per day over a week) rather than in a tight loop. A failure
   under that pattern would be strong evidence of a real bug.
2. Instrument `run_bronze_consumer` itself (not a reproduction outside
   it) during a real failure -- e.g., a temporary `stats_cb` or debug
   log around the `consume_batch()` call and `in_flight` state --
   captured *during* a failing run, not inferred afterward. Every
   diagnosis so far has been from reproductions or post-hoc checks,
   never a direct look inside the real failing call.
3. Check whether the gap correlates with a flush actually being
   in-flight at the moment consumption stalls (i.e. is this a
   resurfacing of the same "busy-wait starves consume_batch()" family
   as the fix above and the original Bronze Consumer livelock, just
   not needing the buffer to be literally full to trigger) or is
   unrelated to threading entirely.

**Not blocking**: streaming Bronze (the Frente 3 CDC-provenance work)
has no real downstream consumer yet, and this is one `real_kafka`-
marked integration test, excluded from the default suite. Revisit when
there's time for #1-3 above, not urgently.

## `airflow/config/terraform_outputs.json` was one `export-terraform-outputs.sh` run away from leaking real AWS secret keys into git history -- fixed

Found live while committing the CloudWatch-ARN-via-Terraform work
(this same session): `terraform output -json` (what
`scripts/export-terraform-outputs.sh` has always used) does **not**
mask `sensitive = true` outputs the way plain `terraform output` does
-- every IAM access-key/secret-key pair this project has
(`bi_reader_*`, `airflow_ingest_*`, `bronze_consumer_*`,
`dbt_gold_*`) lands in that file in real plaintext. The file is
tracked in git, not gitignored.

**Why this hadn't already happened**: the export script had a
pre-existing path bug (relative paths that only resolved correctly if
invoked from the repo root, while `terraform output` needs to run
against the `environments/dev` working directory -- two incompatible
CWD requirements in one un-`cd`'d script), broken since before this
project had any `sensitive` Terraform outputs at all (the file's only
git history entry, one commit, predates `bi_reader`/`airflow_ingest`/
`bronze_consumer`/`dbt_gold` entirely -- confirmed by reading that
commit's content directly: 7 outputs, all non-sensitive, zero
`secret`/`access_key` fields). The script silently never got
successfully re-run since, so the exposure never had a chance to
surface -- fixing the path bug today (to wire
`AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN` through it) is what made the script
runnable again, which is what surfaced this.

**Confirmed clean, not assumed**: `git log --all --full-history` for
this path returns exactly one commit; its content was checked
directly (`git show <hash>:path | grep -i "secret\|access_key"`) --
zero matches. No real secret was ever actually committed, at any
point, on any branch. The one working-tree version that *did* briefly
contain real values (written by this session's own test run of the
freshly-fixed script) was caught before `git add`, never staged, never
committed.

**Fixed**: `airflow/config/terraform_outputs.json` added to
`.gitignore` (Terraform section, alongside `*.tfstate`/`*.tfvars` --
same reasoning, a Terraform-derived artifact that can carry real
secrets). Removed from the git index with `git rm --cached` (file kept
on disk -- it's meant to be generated locally by
`scripts/export-terraform-outputs.sh` and read by
`airflow/config/bootstrap/terraform.py` at container-bootstrap time,
never version-controlled). Regenerating it locally after the `.gitignore`
change confirmed it's correctly ignored going forward.

## `products`' drain throughput plateaued mid-reprocess (~227-249 msg/min -> ~150 msg/min) -- real, sustained, not write-side, cause not fully identified

Noticed while tracking the Frente 3 reprocess's own drain (not one of
the 8 items committed this session -- a live observation during
monitoring). `products` (the slowest-draining entity, the one that
sets the realistic zero-ETA for all 16) held ~227-249 msg/min from
~16:16 to ~16:47Z, then dropped to and stably held ~147-152 msg/min
from ~16:47Z onward (confirmed via a 53-minute window, not a short
noisy sample: `mdp_bronze_consumer_lag` at 17:49Z vs 18:42Z gives the
same ~147/min the short samples around it show) -- a real, sustained
step change, not measurement noise, and not still declining.

**Ruled out, checked directly, not assumed**: write-side slowness or
errors. Zero `mdp_bronze_write_failures_total` for `products` the
entire container lifetime. `mdp_bronze_write_duration_seconds` sampled
in a real live window (not the cumulative average) came back ~2.25s/
write, faster than the cumulative average (~4.0s/write) -- if
anything, writes got quicker, not slower, around the same time
throughput dropped. `mdp_bronze_records_written_total` divides evenly
by 100 throughout, confirming every flush is a full batch (size-
triggered), not partial/age-triggered ones sneaking in.

**Correlated in timing with 3 entities reaching zero lag, not
confirmed as causal**: the deceleration window (~16:47-17:18Z) is
exactly when `customers`, `order_items` and `customer_addresses` went
from near-zero to zero (session's own progress reports: "6/16 zeradas"
at ~16:47Z, "9/16 zeradas" at ~17:18Z) -- suggestive of some kind of
round-robin/flush-pool reallocation effect among the remaining active
entities as others drop out, the opposite direction from the naive
"fewer entities competing for the 8-worker pool should mean *more*
throughput for the ones left" expectation. Whether the freed capacity
actually went to the other still-heavy entities (`inventories`,
`inventory_movements`, `orders`, `order_status_history`) instead of
`products` specifically was not confirmed -- would need reliable
per-entity throughput numbers for all of them across the same window,
not just `products`' (which is all that was reliably on hand at
investigation time).

**Not investigated further**: real finding, but not urgent -- writes
are healthy, the container is stable, the reprocess keeps draining
(just slower than the earlier rate for this one entity). Revisit if a
similar step-change recurs and reliable multi-entity throughput
history is available to check the reallocation hypothesis properly.

## `docker-compose.yml`'s working tree isn't just a staging area, it's what Compose reconciles live infra against -- found live, real (contained) side effect

Found during the round-robin/init:true/credential-swap restart
(2026-08-10): a deferred, not-yet-decided diff (`mdp-kafka`'s memory
limit, 768M -> 1024M -- see that entry above) had been left sitting,
uncommitted, in `docker-compose.yml`'s working tree for safekeeping --
the same pattern already used safely, repeatedly, for
`roadmap-next-steps.md` and `test_bronze_consumer.py` earlier this
same session (temporarily strip a pending hunk out for an isolated
commit, restore it afterward). That pattern is safe for files nothing
*reads at runtime* -- it broke here because `docker compose up`
doesn't consult git at all; it diffs the live YAML file on disk
against each running container's actual config. Running `docker
compose up -d bronze-consumer` (only bronze-consumer named explicitly)
still recreated `mdp-kafka` too, because Compose noticed `mdp-kafka`'s
service definition in the file had drifted from the container
actually running (768M live vs. 1024M in the file) and reconciled it
as part of the same `up` invocation -- an unapproved, unintended
change reaching real infra as a side effect of file hygiene, not a
deploy command targeting Kafka.

**Impact, checked, not assumed**: `mdp-kafka` recreated at the new
1024M limit, ~54s of restart. `cluster.id` unchanged
(`MkU3OEVBNTcwNTJENDM2Qk` before and after -- same cluster, not a
fresh one), data volume (`docker_kafka_data`) intact, no errors in
Kafka or Debezium logs across the restart window, `kafka-consumer-groups
--describe`'s real per-partition offsets showed normal continued
draining (not reset) once cross-checked. See the next entry for why
the *Prometheus* lag metric looked far worse than this for a few
minutes despite that. Reverted back to 768M the same session, once
found -- see git history around this entry's timestamp.

**New rule, going forward**: a deferred/not-yet-approved
`docker-compose.yml` (or any Compose file) hunk does **not** get
restored into the working tree while it stays pending, unlike
docs/test files. It's kept instead as a standalone patch under
`docs/architecture/deferred-patches/` (`git diff` output, `git apply`
when actually decided) or pasted inline in its own roadmap entry --
either way, never sitting in a file Compose itself reads to decide
what to reconcile.

## `mdp_bronze_consumer_lag` can read far higher than reality for a few minutes right after a consumer restart -- known limitation, not urgent

Found during the same 2026-08-10 restart above: right after
`bronze-consumer` came back up, the Prometheus metric showed
dramatic-looking jumps (e.g. `orders` 14,107 -> 187,029, `products`
116,915 -> 212,379) that read like a consumer-group offset reset --
alarming enough to stop and investigate before touching anything else.
Cross-checked against the authoritative source
(`kafka-consumer-groups --describe`, which reads the broker's actual
committed offsets) instead of trusting the exported metric: real lag
was normal and continuing to drain (`orders` ~12,307, actually *lower*
than the pre-restart baseline; `products` ~115,015, essentially flat)
-- no reset, no reprocessing from scratch, no data loss.

**Suspected mechanism (plausible, not proven to 100% -- accepted as
such, not urgent to chase further)**: `KafkaMessagingProvider.consumer_lag()`
(`src/integrations/kafka/messaging/kafka_messaging_provider.py`) calls
`consumer.position(assignment)` and falls back to the partition's low
watermark whenever a partition reports `OFFSET_INVALID` (its
documented behavior for "never consumed from yet in this Consumer
instance"). Right after a fresh process restart, before a newly
recreated `Consumer`'s local position cache has synced with the
group's real committed offset from the broker, `position()` can still
return `OFFSET_INVALID` for a partition even though the broker itself
already has a valid committed offset for it -- inflating the computed
lag toward "as if starting from the beginning" until that first sync
completes, typically within the first couple of poll cycles per
entity.

**Practical takeaway, not a fix**: for the first few minutes after any
`bronze-consumer` restart, don't trust `mdp_bronze_consumer_lag` at
face value -- cross-check against `kafka-consumer-groups --describe`
(the real, broker-side number) before reacting to what looks like a
regression. Not fixed or further investigated this session -- flagged
so a future restart doesn't cause the same alarm.

## Frente 3 (CDC provenance) close-out: the full 16-entity reprocess drained to zero, final validation done against real data before committing

**Reprocess status, confirmed live via `kafka-consumer-groups --describe`
(not the Prometheus metric -- see the entry above)**: aggregate lag
reached and held at **0 across all 16 entities**, `mdp-kafka` stable
at 768M, `bronze-consumer` healthy, no errors, for the remainder of
this session after the round-robin tuning + init:true + credential-swap
restart. This is the state the whole day's monitoring (livelock fix,
IAM work, throughput tuning, the Kafka-recreate incident above) was
building toward -- see this file's earlier entries for that history.

**Schema, checked against every one of the 16 real streaming Bronze
tables (`StorageConfig.bronze()`, not the batch table)**: `_cdc_ts_ms`
(int64) present with zero nulls in all 16.

**Row counts, real Bronze vs. real Postgres, all 16 entities** (Bronze
is append-only CDC history, so counts exceeding Postgres's current
live row count is expected by design, not itself a problem -- see this
module's own docstring): the 8 entities that hit the commit-failure
livelock earlier today (`payments`, `inventory_movements`,
`order_status_history`, `reviews`, `shipments`, `products`, `orders`,
`warehouses`) show a Bronze/Postgres ratio of ~1.86x-2.83x; the
remaining 8 show ~1.0x-1.35x. This split lines up exactly with the
livelock's own already-documented, already-fixed duplicate-on-retry
mechanism (see "Bronze Consumer's commit-failure retry can livelock an
entity permanently" above) -- an entity that hit the livelock re-wrote
its already-committed-but-uncommitted batch once before the fix
unblocked it, which is consistent with the roughly-2x-vs-roughly-1x
split observed. Not a new issue, and expected going in (see the
handoff prompt that opened this session).

**A genuine outlier investigated, not waved off**: `categories` showed
150,068 Bronze rows against only 10 live Postgres rows (a ~15,007x
ratio, wildly outside every other entity's range) and only 5 distinct
`_cdc_ts_ms` values for those 150,068 rows -- initially indistinguishable
from a duplicate-write bug. Root-caused instead of assumed:
- 150,055 of those rows share one `_cdc_ts_ms`
  (`1785786209431`) and are a real Debezium `"d"` (delete) op, same
  `txId` (`44128`) across a raw-Kafka sample -- i.e. one single bulk
  DELETE transaction, and Debezium's `source.ts_ms` is the
  transaction's commit time, legitimately shared by every row it
  touched (not a retry artifact). `before.name` is empty/placeholder
  on these rows -- `categories` isn't configured with `REPLICA IDENTITY
  FULL`, so a delete's `before` image only carries the real primary key,
  not the deleted row's actual prior content; a pre-existing,
  orthogonal limitation, not something this session's work touched.
- That transaction's 99,155 distinct `category_id`s match, almost
  exactly, the historical bug this codebase already found and fixed
  this month: commit `e726537` ("fix(simulator): stop categories from
  growing without bound", 2026-08-03) -- `CategoryService.create_category()`
  used to insert a brand-new `category_id` every cycle with no
  dedup/unique constraint, confirmed in that commit's own message
  against real data at the time ("134,207 rows, only 10 distinct
  names"). This 5-`ts_ms` cluster is that bug's real cleanup: the mass
  DELETE removing the accumulated duplicates, plus a small 10-row `"c"`
  reseed batch (`ts_ms=1786216913652`, matching today's 10 live
  category names exactly) and 3 singleton real updates. Bronze
  faithfully recorded a real, large, legitimate transaction -- not a
  bug in the Kafka/bronze-consumer/Bronze path.

**`_deduplicate_by_key` validated against real data, not just synthetic
unit tests**: pulled real multi-version Bronze rows for two actual
`category_id`s (one with 4 genuine versions of "Fashion" at 4 distinct
real timestamps, one with a single row) into a local Spark session and
ran `apply_standard_transformations(df, natural_key_columns=["category_id"],
order_column="cdc_ts_ms")` against them directly -- confirmed
programmatically (not just visually) that it reduces to exactly one
row per real key, keeping the one with the true maximum `_cdc_ts_ms`
each time. No manual Bronze cleanup needed for `categories` or anything
else -- the dedup step already resolves this exactly as designed once
an entity is actually built from streaming Bronze (still no real
caller does that yet, per `apply_standard_transformations`' own
docstring).

**Conclusion**: nothing found blocks this close-out commit. Every
inflated count traces to either normal, documented Debezium snapshot
behavior, the already-fixed simulator bug above, or the
already-fixed-today livelock's own accepted duplicate-on-retry
tradeoff -- and the dedup path meant to resolve all of it at the
Silver layer is confirmed working against real data, not just
synthetic fixtures.

## `Pipeline.__iter__`'s declared return type doesn't match what it actually yields -- found during this session's repo-wide mypy sweep, not fixed

`uv run mypy src/data_platform/processing/core/pipeline.py`:

```
pipeline.py:97: error: Incompatible return value type
  (got "Iterator[Stage | None]", expected "Iterator[Stage]")  [return-value]
```

`Pipeline.__iter__` is declared `-> Iterator[Stage]` but returns
`self._flatten()`, whose real signature is `-> Iterator[Stage | None]`
-- `_flatten()` can yield `None` (see its own docstring: "only
`__post_init__`'s own validation loop ever sees that case"). In
practice this is safe: `__post_init__` walks `_flatten()` once at
construction time specifically to reject any `None` with a
`ValueError` before the `Pipeline` object is ever handed back to a
caller, so no `Pipeline` that survived construction can yield `None`
on a later `__iter__()` call -- but that guarantee lives in
`__post_init__`'s logic, not in `_flatten()`'s type signature, so
mypy has no way to verify it and correctly flags the mismatch.

**Not fixed**: found live during this session's repo-wide `ruff`/mypy
sweep, alongside unrelated fixes; deliberately not touched then to
keep that sweep's own commit scoped to what it was already doing.
Options, not decided: (a) `# type: ignore[return-value]` on
`__iter__` with a comment pointing at `__post_init__`'s invariant, (b)
a private `_flatten_validated() -> Iterator[Stage]` that asserts
non-`None` per item (turns a real-but-currently-impossible case into
an explicit `AssertionError` instead of a silent type lie), or (c)
give `_flatten()` two callers with different signatures instead of
sharing one. No real behavior is wrong today -- this is a type-safety
gap, not a runtime bug.

## Sprint 13 (Observability) close-out, part 1: the 5 unwired CloudWatch log groups -- resolved per log group, not uniformly

Picked up from "Airflow remote logging is AWS-coupled by construction"
and the README's own "The other 5 log groups (Athena, Databricks,
Glue, platform, Terraform) not wired" line. Investigated each of the 5
individually rather than treating them as one uniform task -- they
turned out to need 3 different answers, not one:

**`glue` and `athena` -- removed from Terraform, not wired.** Confirmed
against AWS's own docs before deciding, not assumed:
- Glue's CloudWatch logging is opt-in per job
  (`--enable-continuous-cloudwatch-log`, docs.aws.amazon.com/glue/
  latest/dg/monitor-continuous-logging-enable.html) -- and this
  project has zero Glue Jobs/Crawlers to attach it to (only Glue Data
  Catalog databases via `module.catalog`, confirmed via
  `grep -rln aws_glue_crawler infrastructure/terraform/`).
- Athena has no CloudWatch *Logs* mechanism at all for query
  execution -- only CloudWatch *metrics* and CloudTrail API audit
  (docs.aws.amazon.com/athena/latest/ug/
  security-logging-monitoring.html lists exactly those two, nothing
  else).

Both log groups had zero possible producer, ever -- dead
infrastructure by design, same disposal criteria ADR-013 already used
for the `ingestion/` package. `terraform plan` confirmed exactly `2 to
destroy, 0 to add/change` before applying; `aws logs
describe-log-groups` confirmed only `airflow`/`databricks`/
`platform`/`terraform` remain.

**`platform` -- wired for real, validated live.** `configure_logging()`
(`data_platform/observability/logging_config.py`) gained an additive
structlog processor (`_ship_to_cloudwatch`, runs after `JSONRenderer`)
that ships the exact same JSON lines the console already prints to a
`watchtower.CloudWatchLogHandler`, gated by
`LOG_CLOUDWATCH_ENABLED`/`LOG_CLOUDWATCH_LOG_GROUP` -- console output
via `PrintLoggerFactory` is untouched either way. A CloudWatch failure
disables shipping for the rest of the process (warns once on stderr,
never crashes the caller) -- this protects a long-running process
(bronze-consumer), a different trade-off than the two shippers below.
IAM: `mdp-airflow-ingest-dev` and `mdp-bronze-consumer-dev` both
gained a `CloudWatchPlatformLogs` statement (`CreateLogGroup`/
`CreateLogStream`/`DescribeLogStreams`/`PutLogEvents`/`GetLogEvents`,
mirroring the existing `CloudWatchAirflowLogs` statement's own
reasoning for why `CreateLogGroup` is needed even though the group
pre-exists). `watchtower` added as a core dependency
(`pyproject.toml`), plus into `infrastructure/docker/airflow/
Dockerfile`'s manually-mirrored dependency list (see the gap this
missed, below). Validated live: real bronze-consumer startup log
lines (`Metrics server started.`, `Bronze Consumer starting.`)
confirmed via `aws logs get-log-events` against `/mdp/dev/platform`.

**`terraform` -- wired via an optional wrapper, validated live.**
`scripts/terraform_with_cloudwatch_logging.py` -- runs
`terraform -chdir=.../environments/dev <args>` as a subprocess,
mirrors its combined stdout/stderr to the console unchanged, and ships
each line to `/mdp/dev/terraform` via the same watchtower pattern.
Deliberately optional, not a replacement for running `terraform`
directly (this project's own day-to-day workflow, this session
included, still does that) -- an opt-in second way to get a durable,
queryable record of a real plan/apply's terminal output. Runs under
whatever credential the caller's shell already has for Terraform
itself (the personal `terraform-admin` key) -- already broad enough
(`logs:*`), no new IAM needed. Unlike the `platform` handler, a
CloudWatch failure here is surfaced on stderr, not silently swallowed
-- a short-lived, interactively-run wrapper around a real
infrastructure mutation should make a broken audit trail visible, not
hide it (it still never fails the terraform run itself over a logging
concern). Validated live: a real `terraform plan` (`No changes`, exit
0) shipped 76 real events to `/mdp/dev/terraform`, confirmed via `aws
logs get-log-events`.

**`databricks` -- wired via a new Airflow task, event-driven, validated
against a real "Full Pipeline" run.** New module,
`integrations/databricks/observability/run_output_shipper.py`
(same domain-module pattern as `integrations/kafka/messaging/`),
deliberately Airflow-agnostic -- takes an already-authenticated
`WorkspaceClient`, doesn't import Airflow. `marketplace_batch_pipeline.py`
gained `ship_databricks_run_logs`, a `@task` running in **parallel** to
`dbt_run_gold` (`run_full_pipeline >> [dbt_run_gold,
ship_databricks_run_logs()]`), not upstream of it -- a shipping
failure must never block the real Gold build. Confirmed before
building: the 3 real Jobs (`bronze`/`silver`/`full_pipeline`) all run
on **serverless** compute (`environment_key`, no `new_cluster`/
`existing_cluster` in any `*_job.yml`) -- no `cluster_log_conf`
possible, so the Jobs API's `get-run-output` (capped at 5MB by the API
itself, docs.databricks.com/api/workspace/jobs/getrunoutput) is the
only reachable log-shaped signal, not full driver/executor logs.
Builds its own `WorkspaceClient(host=, token=)` from the
`databricks_default` Connection -- deliberately not
`DatabricksContext.workspace`, which resolves `~/.databrickscfg`'s
`modern-data-platform` profile (expired, see
`docs/environment-inventory.md`, and the wrong auth mechanism for a
process running inside the Airflow container regardless). IAM
deliberately narrower than `platform`'s: only `CreateLogStream`/
`PutLogEvents` on `mdp-airflow-ingest-dev` -- no `CreateLogGroup`
(confirmed by reading watchtower's own source: it only calls
`CreateLogGroup` when `create_log_group=True`, and this code passes
`False`) and no `DescribeLogStreams`/`GetLogEvents` (watchtower's
write path never calls either -- confirmed the same way). **This is
more precise than `platform`'s own grant above, which included those
3 unused actions for consistency with the pre-existing Airflow
statement -- worth revisiting `platform`'s grant down to the same
minimal set in a future pass, not done here** (both work today; this
is a least-privilege tightening opportunity, not a bug).

Validated live against a real scheduled run
(`scheduled__2026-08-11T12:55:24...`): `run_databricks_full_pipeline`
succeeded (~10 min), `ship_databricks_run_logs` shipped 4 real events
(one per sub-task -- `bronze`/`bronze_validate`/`bronze_optimize`/
`silver`, all `TERMINATED`/`SUCCESS`) to `/mdp/dev/databricks`,
confirmed via `aws logs get-log-events`. A genuine, harmless API quirk
found along the way: `RunOutput.error` is populated with a generic
placeholder string ("Please refer to the logs for this run on the
triggered run details page.") even on success, not only on failure --
`_format_task_output()` includes it whenever present, which reads as
if every task had an error; cosmetic, not fixed here, easy to filter
on `result_state` if it becomes confusing in practice.

**Two real, live-caught bugs found validating the above, both fixed
before the final passing run:**

1. **`infrastructure/docker/airflow/Dockerfile`'s manually-mirrored
   dependency list was stale the moment `watchtower` was added to
   `pyproject.toml`.** That Dockerfile's own comment already says
   it's "the full `[project.dependencies]` set ... same version
   floors" -- a second, hand-maintained copy that doesn't update
   itself. Caught live: the very first `ship_databricks_run_logs` run
   (against the *old* image, before the rebuild below) failed with
   `ModuleNotFoundError` for `watchtower` inside the Airflow
   container, even though `bronze-consumer` (built via `uv sync
   --frozen`, no manual mirror) already had it. Fixed by adding
   `watchtower` to the Dockerfile's list and rebuilding.
2. **No `AWS_REGION`/`AWS_DEFAULT_REGION` was ever set for the Airflow
   containers.** `extract_postgres` never needed it by accident --
   `AwsContext`/`AwsSettings` always pass an explicit `region_name` to
   `boto3.Session()` (default `"us-east-1"`, itself the separate,
   already-documented gap in `docs/environment-inventory.md`) -- so
   boto3 never had to resolve a region from the environment.
   `watchtower`'s own internal `boto3.client("logs")` construction has
   no such override and failed with a real
   `botocore.exceptions.NoRegionError` the first time it was actually
   exercised inside an Airflow container (a real
   `ship_databricks_run_logs` failure, not a hypothetical). Fixed by
   adding `AWS_REGION`/`AWS_DEFAULT_REGION: sa-east-1` to
   `x-airflow-common-env` -- same value/reasoning bronze-consumer's
   compose block already carried for the same underlying reason (see
   "`write_deltalake()` ... doesn't follow a cross-region redirect"
   earlier in this file). This also retroactively fixes `platform`'s
   own shipping path for the 3 non-DAG-task `configure_logging()`
   callers that run inside Airflow containers (the 2 one-off scripts,
   the bootstrap script) -- their first real attempt would have hit
   the exact same `NoRegionError`, just not yet observed live before
   this fix landed.

**Remaining Sprint 13 work, not started in this pass**: Grafana
dashboards (only the Prometheus datasource is provisioned today, no
dashboard JSON) and alerting (no `rule_files`/Alertmanager, no Grafana
unified-alerting rules). This entry closes out the "5 unwired log
groups" sub-item only. See the next two entries for both of those.

## Sprint 13 close-out, part 2: Grafana Pipeline Health dashboard, config-as-code

Same session, picked up right after the log-groups close-out above.
First real Grafana dashboard, provisioned as JSON
(`infrastructure/docker/monitoring/grafana/provisioning/dashboards/`,
`dashboard.yml` + `json/gold-layer-pipeline-health.json`,
`allowUiUpdates: false`) -- same "config as code" discipline the
Metabase `Gold Layer Overview` dashboard already established
(`dashboards/metabase/*.sql`, not built through the UI). 11 panels
across all 3 real metric sources this project has
(`data_platform.processing.metrics.prometheus_metrics_hook`, Bronze
Consumer, Airflow via statsd-exporter).

**Every panel's PromQL was built against real metric/label names
confirmed live first, via the Prometheus HTTP API
(`/api/v1/label/__name__/values`, `/api/v1/query`), not guessed from
the instrumentation code or the mapping config alone.** This caught
real discrepancies before they became broken panels:
- `airflow_pool_open_slots`/`queued_slots`/`running_slots` genuinely
  are labeled (`{pool="catalog"}` etc.) as `statsd-exporter/
  mapping.yml` intends -- confirmed by querying with labels, not just
  listing `__name__` values (a bare name listing initially looked like
  these were *unlabeled* aggregates, because Prometheus also always
  keeps the label-less catch-all series alongside the labeled ones;
  querying with `{pool=...}` present was what actually settled it).
- `airflow_task_duration_seconds`/`airflow_task_finish_total`/
  `airflow_dagrun_duration_success_seconds` all carry real
  `dag_id`/`task_id`/`state`/`quantile` labels, confirmed the same
  way.
- `mdp_bronze_consumer_lag` and the other 4 Bronze Consumer metrics
  had **zero current samples** at query time -- not a bug, the
  container had just been restarted (Sprint 13 part 1's own
  validation work) and the simulator isn't running (see
  `docs/environment-inventory.md`), so no new Kafka messages had
  flowed since the fresh process's Prometheus registry reset. A 7-day
  range query (`metric[7d]`) confirmed all 16 real entity series exist
  with thousands of historical samples each -- the dashboard's queries
  are correct, there just wasn't live data at that exact moment.

**A real, live-caught mistake, not a hypothetical one:** tried pinning
the Prometheus datasource's `uid` to an explicit `"prometheus"` value
in `datasources/prometheus.yml`, specifically so the dashboard JSON's
`datasource.uid` references would be reproducible/portable rather than
depending on whatever id Grafana happened to auto-assign. Broke
Grafana startup outright against this real, already-running instance:
`docker compose restart grafana` (itself blocked the first time by the
zombie-PID-1 issue below, need to be recreated instead) came back with
every module failing to start, root cause `"Datasource provisioning
error: data source not found"`. Root cause, confirmed via the
container's own logs, not guessed: `grafana_data` is a persistent
Docker volume, and this datasource was already created weeks ago
(Decision 4, the original Prometheus+Grafana sprint) under Grafana's
own auto-generated `uid` -- file-based datasource provisioning matches
by `name` to update an existing datasource, but changing its `uid`
this way isn't supported; the mismatch between the file's new uid and
the database's stored one broke the whole provisioning module, which
several other Grafana modules depend on to start at all. **Fixed**:
reverted the `uid: prometheus` line. The dashboard JSON instead
hardcodes the datasource's real, already-assigned uid
(`PBFA97CFB590B2093`, read via `GET /api/datasources`) -- less
elegant than a clean, provisioning-assigned constant, but accurate to
what actually exists on this instance. A fresh `docker compose up`
against an empty volume would auto-assign a uid on first boot too, so
this specific failure mode is really only a risk when re-provisioning
an *existing*, already-populated instance -- worth remembering if this
datasource's config is ever touched again.

**Same zombie-PID-1 issue already fixed for bronze-consumer, hit live
here too** -- first time this session Grafana's own container needed a
real restart (not just a fresh `up`): `docker compose restart grafana`
failed outright, `"container ... is zombie and can not be killed. Use
the --init option"`. Same fix, same reasoning, applied to `grafana`'s
own service block: `init: true`, low-risk and additive.

**Validated live end to end, not just "loaded without a provisioning
error":**
- `GET /api/search?type=dash-db` confirms the dashboard is
  provisioned, correct `uid`/`title`/`tags`.
- `POST /api/ds/query` against the real datasource uid, run through
  Grafana itself (not Prometheus directly) -- confirmed real data for
  an Airflow panel (`airflow_task_finish_total`, a real
  `task_id="entities_parameter"`/`state="success"` series) and a
  Bronze Consumer panel (`mdp_bronze_consumer_lag` over a 24h range,
  15 real entity series with real historical values).

## Sprint 13 close-out, part 3 (final): 4 Grafana alert rules against real metrics, notification delivery deliberately out of scope

Same session, immediately after the dashboard above -- every alert
rule here reuses a query already validated building that dashboard,
not a new, unverified one. Provisioned as code
(`infrastructure/docker/monitoring/grafana/provisioning/alerting/`,
3 files: `rules.yml`, `contactpoints.yml`, `policies.yml`).

**4 rules, one per real signal already on the Pipeline Health
dashboard:**
1. `mdp-pipeline-stale` -- `time() - mdp_pipeline_last_run_timestamp_seconds{job="extract_postgres"} > 5400`
   (90 min, 3x `marketplace_batch_pipeline`'s own 30-min schedule),
   `for: 5m`.
2. `mdp-airflow-scheduler-stalled` -- `rate(airflow_scheduler_heartbeat_total[5m]) < 0.01`
   (not an exact `== 0`, avoids float-precision noise on a real,
   always-incrementing counter), `for: 5m`.
3. `mdp-bronze-write-failures` -- `sum(increase(mdp_bronze_write_failures_total[15m])) > 0`,
   `for: 0m` (fires as soon as observed).
4. `mdp-airflow-task-failures` -- `sum(increase(airflow_task_finish_total{state="failed"}[15m])) > 0`,
   `for: 0m`.

Each uses Grafana's two-stage query model: refId `A` is the real
Prometheus instant query (datasource uid `PBFA97CFB590B2093`, same one
the dashboard uses -- see the entry above for why it's hardcoded, not
provisioning-assigned), refId `B` is a `threshold` expression
(datasource uid `-100`, Grafana's reserved pseudo-datasource for
expressions) evaluating `A` against the real condition.

**Deliberate scope decision, not an oversight:** this dev environment
has no real notification channel configured anywhere --
`docker-compose.yml`/`.env` have no `SMTP_*`, no Slack webhook URL, no
PagerDuty key, nothing. Every alert rule still needs a route to *some*
contact point (Grafana's alerting engine enforces this structurally),
so `contactpoints.yml` defines `mdp-webhook-placeholder`, a `webhook`
receiver pointed at `http://localhost:1/...` -- a port nothing in this
stack (or on the host) ever binds, chosen deliberately so a delivery
attempt fails immediately and unambiguously rather than hanging on a
slow timeout against a URL that merely doesn't resolve. This makes
alert **rule evaluation** (does the condition correctly detect a real
problem against real data) fully real and validatable without also
having to stand up or fake a real SMTP/Slack integration this
environment doesn't have. Notification **delivery** is an explicit,
tracked gap -- revisit when a real channel (Slack webhook is the
lowest-friction option, same reasoning ADR-012 gave Telegram over
WhatsApp for a different channel decision) is actually wanted.

**Validated live via the Grafana alerting API, not just "provisioned
without error":** `GET /api/v1/provisioning/alert-rules` confirms all
4 rules exist with the exact structure written above; `GET
/api/prometheus/grafana/api/v1/rules` (the real, live evaluation
endpoint) shows all 4 with `health: ok`, empty `lastError`, and state
`inactive` -- correctly matching real current conditions at validation
time (the pipeline had completed a run ~10 minutes earlier, the
scheduler's heartbeat was actively incrementing, and neither Bronze
write failures nor Airflow task failures had occurred in the trailing
15-minute window each rule checks -- confirmed against the same real
Prometheus data the rules themselves query, not asserted from the API
response alone).

**Sprint 13 (Observability) is now closed**: logging, metrics,
dashboards and alerting (rule evaluation) are all real, validated
end-to-end against live data -- the one explicitly deferred piece is
alert notification *delivery*, tracked above as its own follow-up, not
silently folded into "done".
