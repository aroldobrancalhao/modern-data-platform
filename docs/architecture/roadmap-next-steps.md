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

## GoldCatalogRegistrationStage (Airflow-side Glue registration)

`publish_gold.ipynb` (N4) only writes the Gold Delta table -- it does
not register it in the Glue Catalog. Databricks Free Edition has no
AWS credential path available inside the notebook (no instance
profile, no cross-account IAM role trust, no secret scope), and
introducing a long-lived AWS access key just for this would break the
project's "no static long-lived credentials" discipline (same reason
there's no static `DATABRICKS_TOKEN`). Instead, after
`full_pipeline.yml`'s `gold` task finishes, Airflow should trigger a
`GoldCatalogRegistrationStage` -- same pattern as the existing
`CatalogPublishingStage`/`GlueCatalogProvider` (already tested against
real Glue, `real_aws` marker) -- that reads the Gold Delta table's
schema and registers it, using the real local AWS credential chain
Airflow already has today. Not implemented yet.

This also happens to help cloud portability rather than hurt it: the
piece running inside Databricks (`read_delta`/`write_delta`, plain
Spark over `s3://` URIs) is already cloud-neutral -- swapping the URI
scheme (e.g. `gs://`) is enough. Keeping catalog registration outside
the compute cluster means a future provider switch (AWS -> GCP) only
swaps the concrete `CatalogProvider` (`GlueCatalogProvider` -> a
future `BigQueryCatalogProvider`) behind the same
`CatalogProvider`/`CatalogContextWriter` contract -- not a redesign of
the flow.
