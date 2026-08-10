# ADR-013 — `src/` Module Structure, Reconciled With Reality

Status: Accepted

---

# Context

ADR-001 and ADR-004 (both dated 2026-07-19) each describe a different
`src/` top-level module list, and neither matches what has actually
existed in this repository for some time:

- **ADR-001** ("Platform Modules" / "Repository Organization"):
  `platform/`, `ingestion/`, `streaming/`, `processing/`, `quality/`,
  `simulator/`, `common/`.
- **ADR-004** ("Source Code Organization"): `platform/`, `cloud/`,
  `ingestion/`, `streaming/`, `processing/`, `quality/`,
  `orchestration/`, `analytics/`, `common/`.
- **Real `src/`** (confirmed by listing the filesystem directly, not
  assumed from either document): `common/`, `data_platform/`,
  `ingestion/`, `integrations/`, `quality/`, `simulator/`,
  `streaming/`.

Found while auditing all ADRs for staleness this project's own
`docs/architecture/roadmap-next-steps.md` already flagged this gap and
deliberately deferred writing the reconciliation ADR until now, rather
than patching either document with a "quick edit" that wouldn't
capture the full picture.

---

# Decision

This ADR is the single source of truth for `src/`'s top-level module
structure going forward, superseding the "Platform Modules" /
"Repository Organization" and "Source Code Organization" sections of
ADR-001 and ADR-004 respectively. The rest of both documents (the
layered architecture, the Medallion layers, the dependency-direction
principles, the naming conventions) is unaffected and remains in
force — this ADR narrowly replaces the module *list*, not the
architectural philosophy behind it.

The real structure is adopted **as-is**, not restructured to match
either prior document — renaming `data_platform/` back to `platform/`
or splitting it into ADR-004's `platform/` + `cloud/` split at this
point would touch a large, working, tested codebase for a purely
cosmetic gain. One exception: `ingestion/` (see below) turned out to
be genuinely dead weight, not a rename or a growth beyond either
prior ADR's description like everything else here — removed as part
of writing this ADR, not left in place for consistency's own sake.

---

# Real `src/` Top-Level Structure

```
src/
    common/
    data_platform/
    integrations/
    quality/
    simulator/
    streaming/
```

## Renames from both prior documents

| ADR-001 / ADR-004 name | Real name | Notes |
|---|---|---|
| `platform/` | `data_platform/` | Same role in both ADRs — infrastructure-independent abstractions (storage, compute, messaging, config, monitoring, security, catalog, providers) — just renamed, and grown considerably beyond either ADR's own submodule list (see below). |
| `cloud/` (ADR-004 only; ADR-001 never split this out) | `integrations/` | Real submodules are per-*integration* (`kafka/`, `postgres/`, `airflow/`, `aws/`, `databricks/`), not per-*cloud-provider* (`aws/`, `azure/`, `gcp/`, `local/`) — `postgres/`, `airflow/` and `databricks/` aren't cloud providers at all in ADR-004's sense, so that document's own organizing principle for this directory doesn't hold even setting the rename aside. |
| `orchestration/`, `analytics/` (ADR-004 only) | *(not separate top-level packages)* | Airflow-specific code lives under `integrations/airflow/`; there is no dedicated `analytics/` package — dbt (`dbt/`, outside `src/`) and Athena access via `data_platform/catalog/` cover what ADR-004 assigned here. |

## `data_platform/` — real submodules, considerably more than either ADR's own list

```
data_platform/
    catalog/       compute/        config/         contracts/
    datalake/       enums/         exceptions/     http/
    identity/      messaging/       models/        monitoring/
    notifications/  observability/ processing/      providers/
    security/      storage/        types/          workflow/
```

ADR-001's list for this package: `config/, storage/, compute/,
messaging/, monitoring/, catalog/, security/, providers/`. ADR-004
added `identity/, notifications/`. Both undercount the real package by
roughly half — `contracts/` (the actual `*Provider` ABCs, e.g.
`MessagingProvider`, referenced throughout
`docs/architecture/roadmap-next-steps.md`), `datalake/`, `enums/`,
`exceptions/`, `http/`, `models/`, `observability/`, `processing/` and
`types/` all exist and are in active use but were never named in
either document.

`processing/` is the largest of these and deserves its own callout:
it's where `PostgresExtractionStage`
(`data_platform/processing/extraction/postgres_extraction_stage.py`)
and the Silver transformation logic
(`data_platform/processing/silver/transformations.py`, both referenced
repeatedly in `roadmap-next-steps.md`) actually live — **not** under
the top-level `ingestion/` package that both ADR-001 and ADR-004 name
for exactly this purpose. Which leads to the most consequential single
finding of this audit:

## `ingestion/` existed as an empty skeleton — removed the same day this was found

```
ingestion/
    __init__.py
    api/__init__.py
    batch/__init__.py
    cdc/__init__.py
```

Every file here was an empty `__init__.py`. Both ADR-001 and ADR-004
describe this package as owning "Database connectors, File ingestion,
API ingestion, CDC consumers" — none of that was here. The real
Postgres batch-extraction logic
(`PostgresExtractionStage`) lives under `data_platform/processing/
extraction/`, and the real CDC consumer
(`streaming/consumers/bronze_consumer.py`, extensively documented in
`roadmap-next-steps.md`'s Frente 3 entries) lives under `streaming/`,
not `ingestion/cdc/`.

**Removed**, same session this ADR was written, not left as a
recorded-but-unaddressed gap: confirmed first, not assumed, that
nothing depended on it -- a full-repo grep for `import ingestion`/
`from ingestion`, any `ingestion.*` string reference, `pyproject.toml`,
Airflow's DAG/pool configs, and every Dockerfile/compose file all came
back clean. The only unrelated hits were a same-named Airflow *pool*
(`airflow/config/pools.json`, a scheduling-concurrency label, nothing
to do with this package) and a `PipelineStage.INGESTION` enum value
(`data_platform/enums/pipeline_stage.py`, a processing-stage name) --
both left untouched, neither references the package. `README.md`'s own
`src/` tree diagram updated to match (it already listed the real
`data_platform/` submodule set accurately, just still carried this one
stale entry).

## The other five packages — real structure matches both ADRs closely, no material discrepancy

```
common/            constants.py, utils.py only -- ADR-004's own
                    description ("shared utilities... exceptions,
                    constants, helpers, logging") overstates it
                    slightly (exceptions/logging actually live under
                    data_platform/exceptions and data_platform/
                    monitoring), but nothing here contradicts either
                    ADR, just narrower in practice than described.

integrations/       airflow/  aws/  databricks/  kafka/  postgres/
                    (see the cloud/ -> integrations/ rename above)

quality/            expectations/  profiling/  validators/
                    -- matches ADR-001/ADR-004 almost exactly.

simulator/          core/  domain/
                    -- matches both ADRs' descriptions.

streaming/          consumers/  producers/  schemas/
                    -- matches ADR-004's own structure for this
                    package exactly.
```

---

# Consequences

- ADR-001's "Platform Modules" and "Repository Organization" sections,
  and ADR-004's "Source Code Organization" section (including its
  `platform/`, `cloud/`, `orchestration/`, `analytics/` subsections),
  are **superseded** by this document. Both ADRs are otherwise
  unchanged and remain the authority on everything else they cover
  (layered architecture, Medallion layers, dependency direction,
  naming conventions, the rest of the top-level repository layout
  outside `src/`).
- Future work referencing "the platform layer" or "the ingestion
  layer" should mean `data_platform/` and (per the finding above) the
  ingestion-shaped code actually under `data_platform/processing/` +
  `streaming/`, not the empty `ingestion/` package.
- `ingestion/` no longer exists in `src/` -- removed rather than left
  as a documented-but-unaddressed gap (see above).

---

# Related ADRs

- ADR-000 – Architecture Principles
- ADR-001 – Platform Architecture (module list superseded by this ADR)
- ADR-004 – Repository Structure (module list superseded by this ADR)
- ADR-002 – Platform Contracts
- ADR-003 – Cloud Strategy
