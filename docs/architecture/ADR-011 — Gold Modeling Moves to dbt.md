# ADR-011 — Gold Modeling Moves to dbt

Status: Accepted

---

# Context

Bronze and Silver run on Databricks/Spark today. `ingest_sources.ipynb`
lands raw Postgres extractions as Bronze Delta tables; `transform_silver.ipynb`
applies `apply_standard_transformations` (column name normalization to
snake_case, string trimming, deduplication, `processed_at`/`processing_date`
metadata) to produce a clean, standardized Silver.

Gold, today, is `publish_gold.ipynb` reading Silver and writing it back
out unchanged — no join, no aggregation, no business rule. This was a
deliberate choice made in N4 ("Silver já entrega dado padronizado, então
Gold só persiste como está, conforme você orientou — sem transformação
de negócio inventada"): at the time, there was no concrete downstream
consumer driving what Gold should actually contain, so inventing
business logic without a real requirement would have been speculative.

ADR-0008 (Batch and Streaming Processing Architecture) already describes
the intended batch flow at a level above any specific tool:

```
SilverService → Silver Data Quality → GoldService → Star Schema
    → Glue Catalog → Athena → Power BI
```

`GoldService` and `Star Schema` were named as roles, not tied to a
specific engine. This ADR is what fills that role in concretely — and,
in doing so, corrects the fact that Gold has had no real modeling
happening in it since it was first implemented.

Separately, the Unity Catalog External Location work (real AWS
credentials reaching Databricks serverless compute via a Storage
Credential, confirmed end-to-end with real Postgres data flowing
through Bronze → Silver → Gold) proved that Databricks' side of the
pipeline is not a toy — it does real, credentialed, production-shaped
ingestion. This decision does not reduce that complexity; it removes a
layer that never had a job to do.

---

# Problem Statement

Two related problems, both structural, not performance-related:

## Gold-on-Databricks is a redundant copy

Since `publish_gold.ipynb` performs no transformation, Gold is
byte-for-byte (modulo file layout) the same data as Silver, stored a
second time under a different S3 prefix. It costs a Databricks Job run,
a second Delta table, and a second Glue registration — for zero
additional value over reading Silver directly.

## Business modeling has no home

Bronze and Silver are, by design, domain-agnostic: `PostgresExtractionStage`
extracts whatever table it's pointed at, and `apply_standard_transformations`
is generic column/row hygiene that doesn't know what a "customer" or an
"order" is. Real marketplace-domain modeling — joining `orders` with
`order_items` and `products`, building a `dim_customers`/`fact_orders`
star schema, encoding business rules specific to this domain — was never
placed anywhere:

- Not in Bronze/Silver: they're intentionally generic (ADR-009's
  processing framework is provider- and domain-independent by design;
  putting business joins there would break that).
- Not in the current Gold: it's a copy, not a modeling layer.

The project's own tech stack (`project-decisions.md`) already commits
to dbt Core for analytical modeling, and ADR-004/ADR-005 already reserve
a `dbt/models/{bronze,silver,gold}` structure and a `stg_`/`int_`/`dim_`/`fact_`
naming convention for it — that space has simply never been used for
real modeling yet.

---

# Decision

**Databricks/Spark's responsibility ends at Silver.** Bronze and Silver
keep running exactly as they do today (ingestion, standardization) —
nothing changes in `ingest_sources.ipynb`, `optimize_bronze.ipynb`,
`validate_bronze.ipynb`, or `transform_silver.ipynb`.

**dbt becomes responsible for Gold**, via the `dbt-athena` adapter,
reading Silver as its source through the Glue Catalog (Athena queries
against the Silver table registered by `GoldCatalogRegistrationStage`
— see below). Modeling follows the Medallion layering already
established in ADR-005:

```
Silver (Glue/Athena source)
    │
    ▼
stg_*        (dbt/models/silver or bronze, per ADR-004 layout — one
              staging model per source table, light renaming/typing)
    │
    ▼
int_*        (intermediate — joins across entities, business rules)
    │
    ▼
dim_* / fact_*   (dbt/models/gold — the real star schema)
```

**`GoldCatalogRegistrationStage` now registers Silver in Glue, not
Gold.** It is, today, the only thing that puts a Delta table backed by
this pipeline into a queryable state for anything outside Databricks —
dbt-athena needs exactly that for its source, just one layer earlier
than before.

---

# What Changes in the System

| Component | Before | After |
|---|---|---|
| `ingest_sources.ipynb`, `optimize_bronze.ipynb`, `validate_bronze.ipynb`, `transform_silver.ipynb` | Unchanged | Unchanged |
| `publish_gold.ipynb` / "Gold Pipeline" Databricks Job | Copies Silver to Gold, no transformation | Removed |
| `full_pipeline.yml` | `bronze → bronze_validate → bronze_optimize → silver → gold` | `gold` task removed from the chain; ends at `silver` |
| `GoldCatalogRegistrationStage` | Registers `gold/{entity}` in Glue | Renamed to `SilverCatalogRegistrationStage` — registers `silver/{entity}` in Glue |
| Gold layer | A second Delta table Databricks writes | dbt models materialized under `dbt/models/gold/` (dbt's own materialization — table/view/incremental, dbt's choice, not Spark's) |
| ADR-0008 Batch Flow diagram | `GoldService` role unassigned | `GoldService`/`Star Schema` role fulfilled by dbt, reading via Athena |

`bronze/` and `silver/` S3 prefixes, `PostgresExtractionStage`,
`apply_standard_transformations`, the Unity Catalog External Location,
and the Bronze/Silver Databricks Jobs are all unaffected.

---

# Resolved Decisions

Both items below were open questions in an earlier draft of this ADR;
both are now decided and implemented.

## 1. `publish_gold.ipynb` and the "Gold Pipeline" Job: removed

Decision: **removed**, not kept as documented dead code.

Rationale: no dead code sitting in the repo that looks live (a future
reader — including a future session of mine — could reasonably assume
a notebook present in `notebooks/gold/` and wired into a `gold_job.yml`
is part of the real flow, and waste time reconciling it against this
ADR). Deleting is fully recoverable from git history if this decision
is ever reversed. Matches how this project has already handled other
retired/replaced pieces (no precedent here for keeping deliberately-
dead notebooks around). The trade-off accepted: losing at-a-glance
visibility into "what Gold used to look like" without checking out an
old commit, and a small amount of rework if this decision is reversed
later (recreating the Job/notebook, though the content itself is
trivial — a few lines).

## 2. `GoldCatalogRegistrationStage`: renamed to `SilverCatalogRegistrationStage`

The class now registers Silver, not Gold — its name said the opposite
of what it does.

Decision: **renamed** to `SilverCatalogRegistrationStage`.

Rationale: name matches behavior; avoids the exact kind of staleness
this ADR itself is partly about (Gold's name outliving its purpose).
"Gold" appeared nowhere in its actual logic (`_read_delta_schema`,
`_to_glue_type`, `create_table`) except the class name and the default
`database` parameter value — leaving the name would have been actively
misleading to the next reader. The rename touched the Stage class, its
module path (now `processing/catalog/silver_catalog_registration_stage.py`),
its one-off script (`scripts/run_silver_catalog_registration_once.py`),
and its tests (unit + real) — mechanical churn, entirely test-covered,
low risk.

---

# Alternatives Considered

## Keep Gold-on-Databricks, add dbt on top of it anyway

Run dbt against the (still redundant) Gold Databricks writes instead of
Silver. Rejected: doesn't remove the duplication that's the actual
problem — just adds a second modeling layer on top of a copy, with no
offsetting benefit.

## Move business/star-schema modeling into Silver's Spark code

Extend `apply_standard_transformations` or add a new Spark step to do
the joins and dimensional modeling in PySpark instead of dbt. Rejected:
breaks the domain-agnostic design of Bronze/Silver established in
ADR-009 (the processing framework's Stages are meant to be
provider/domain-independent), and duplicates work dbt already exists in
this stack specifically to do (`project-decisions.md`'s technology
stack already names dbt Core for analytical modeling — this isn't
introducing a new tool, it's finally using the one already committed
to).

## Databricks SQL / Unity Catalog-native modeling instead of dbt

Use Databricks' own SQL layer (materialized views, DLT) for the star
schema instead of dbt-athena. Rejected: the project's stack decision
already names dbt (not Databricks SQL) for this role, and Databricks
Free Edition's Unity Catalog storage access is already the source of
several real constraints this session (external access, credential
vending) — adding another Databricks-native dependency for modeling
would deepen coupling to a single vendor the project is explicitly
trying to stay agnostic of (`project-decisions.md`: "Cloud Agnostic").

---

# Consequences

## Positive

- Removes a data copy with no technical purpose — one fewer Delta
  table, one fewer Databricks Job run, one fewer Glue registration per
  pipeline run.
- Gives business/domain modeling (joins, star schema, marketplace-specific
  rules) an actual home, using the tool this project already committed
  to for that job.
- Cleaner separation of responsibility by tool: Spark does ingestion
  and generic standardization (what it's good at); dbt does modeling,
  data tests, and versioned documentation/lineage (what it's good at).
- Matches how mature data platforms commonly split this work — not a
  simplification specific to this project's scale.
- `GoldCatalogRegistrationStage`'s existing real-AWS test coverage
  (Glue/Athena format fix, just landed) carries over directly to
  registering Silver instead of Gold — no new integration risk
  introduced by the retarget itself.

## Negative

- One more moving part in the overall pipeline (dbt joins Airflow and
  Databricks as a third orchestrated tool), though this was already
  planned in the tech stack, not new scope.
- dbt's Gold models depend on Silver's schema being registered in Glue
  accurately — any future schema drift in Silver now has a second
  consumer (dbt, in addition to whoever reads Silver directly) that
  needs to tolerate or fail loudly on it.
- `publish_gold.ipynb`/the Gold Job are removed (see Resolved
  Decisions), so reversing this decision later means rewriting them
  from scratch (small effort, but not zero).
- Existing consumers of `gold/{entity}` in S3 or `mdp_gold_dev` in Glue
  (if any exist outside this codebase) would need to be pointed at
  wherever dbt materializes its Gold models instead.

---

# Migration Notes

Non-binding outline for whoever implements this — not committed to as
part of this ADR:

1. Retarget `GoldCatalogRegistrationStage` (or its renamed
   successor) to read/register `silver/{entity}` instead of
   `gold/{entity}`; update its default `database` parameter and its
   real/unit tests accordingly.
2. Remove (or retire, per Open Question 1) `gold_job.yml` and the
   `gold` task in `full_pipeline.yml`; remove (or retire)
   `notebooks/gold/publish_gold.ipynb`.
3. Scaffold `dbt/` per the ADR-004 layout (`models/{bronze,silver,gold}`,
   `snapshots/`, `seeds/`, `tests/`, `macros/`), configure the
   `dbt-athena` adapter against the workgroup/database already
   provisioned (`mdp-athena-dev`, `mdp_silver_dev` once the retarget in
   step 1 lands).
4. Build `stg_*` models per Silver source table, `int_*` models for
   cross-entity joins/business rules, and the `dim_*`/`fact_*` star
   schema under `models/gold/`, per ADR-005's naming convention.
5. Update ADR-0008's Batch Flow diagram to name dbt explicitly in the
   `GoldService`/`Star Schema` step, once implemented.
