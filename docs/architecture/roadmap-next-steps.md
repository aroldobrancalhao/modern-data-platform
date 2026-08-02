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

## Databricks S3 access (Unity Catalog External Location)

**What's blocked**: any S3 read/write from inside the Databricks
cluster (`read_raw`/`read_delta`/`write_delta`, every layer -- bronze,
silver, gold) fails with `SparkException [UNAUTHORIZED_ACCESS]`,
`credentials-provider: AnonymousAWSCredentials` -- the serverless
cluster has no AWS credential reaching it at all.

**Evidence**: run
https://dbc-482c0db5-7f8e.cloud.databricks.com/?o=7474655351834045#job/353523406588616/run/850177561963079
(task `bronze`, notebook `ingest_sources.ipynb`, line
`raw_df.printSchema()`).

**Technical lead**: the stacktrace shows
`com.databricks.unity.UCSManager$.withTemporaryScope` -- external
storage access in this workspace goes through Unity Catalog, not raw
Hadoop S3A (`fs.s3a.access.key`). This suggests the correct fix is
configuring a Unity Catalog External Location + Storage Credential
pointing at `mdp-datalake-dev-857854758128` -- not an environment
variable or a loose key.

**Why this isn't code**: this is Databricks workspace infrastructure
configuration (workspace admin console, or a
`databricks_external_location`/`databricks_storage_credential`
Terraform resource if we want it versioned) -- not something fixable
by changing `src/` or the notebooks alone.

**Deliberately not done**: same call as N4 -- no long-lived AWS key
via a Databricks secret scope just to work around this.

**Status**: the full pipeline (N1-N5) is implemented and tested in
isolation, but the first real end-to-end Databricks run is blocked on
this until the External Location is configured.

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
