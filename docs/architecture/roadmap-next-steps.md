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
