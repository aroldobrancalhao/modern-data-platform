# Metabase — Gold Layer Overview

First real dashboard built on top of the Gold layer, via Metabase
connected to Athena (see `docs/architecture/roadmap-next-steps.md` for
the IAM/location work that made this connection possible). Built via
the Metabase API (`POST /api/card`, `PUT /api/card/:id`, `PUT
/api/dashboard/:id`), not the visual query builder or the dashboard
editor UI — every question here is **Native Query (SQL)**,
specifically so it stays versionable as plain text in this directory
instead of living only inside Metabase's own Postgres metadata
database.

**Why SQL files instead of Metabase's own export**: Metabase's
Serialization feature (the built-in way to export/import
dashboards+questions as YAML) is Pro/Enterprise-only — not available
on the open-source edition this project runs. The `.sql` files here
are the actual source of truth; the Metabase questions are a build
artifact of them, not the other way around.

## Dashboard

**Gold Layer Overview** — `http://localhost:3001/dashboard/2`

| # | File | Question | Card ID | Chart |
|---|------|----------|---------|-------|
| 1 | `01_total_orders.sql` | Total de Pedidos | 40 | scalar |
| 2 | `02_orders_by_day.sql` | Pedidos por Dia | 41 | bar |
| 3 | `03_top_products_by_revenue.sql` | Top Produtos por Receita | 42 | row (horizontal bar) |
| 4 | `04_top_sellers_by_orders.sql` | Top Vendedores por Nº de Pedidos | 43 | row (horizontal bar) |
| 5 | `05_average_order_value.sql` | Ticket Médio | 44 | scalar |

Layout: the two scalars side by side on top, "Pedidos por Dia"
full-width below them, the two `row` charts side by side (2 columns)
at the bottom.

## Data caveats (checked before building, not assumed)

The underlying dataset is simulator-generated, and a few dimensions
don't behave the way a real marketplace's would. Checked the
cardinality of each metric against real Athena data before deciding
whether it was worth building:

- **`order_status` has cardinality 1** (only `PENDING` exists today —
  see `docs/architecture/roadmap-next-steps.md`, "Simulator -- order
  status progression engine"). No "orders by status" metric here —
  it would just be a single bar, misleading as a dashboard tile.
- **`customers`, `products`, and `orders` are all ~137k rows, roughly
  1:1** — the simulator doesn't generate realistic reuse (a customer
  placing multiple orders, a product sold to multiple customers). A
  naive "orders per customer" or "orders per product" metric would be
  flat (~1.0) and not worth showing.
- **`sellers` is also ~137k rows, but real reuse *does* exist one
  level down**: only 24,243 distinct sellers actually appear in
  `int_order_items_enriched` (a seller's *products* get ordered
  repeatedly even though the `sellers` table itself doesn't get
  reused as a foreign key the way a real marketplace would show
  repeat customers). Confirmed real variation before building
  "Top Vendedores por Nº de Pedidos": average ~5.7 distinct
  orders/seller, top seller at 295 — checked with
  `count(distinct order_id)`, not `count(*)`, since one order can
  carry multiple line items from the same seller.
- **Products, by contrast, do show real reuse at the line-item
  level**: 40,113 distinct `product_id` across 137,207 order-item
  rows (~3.4 line items/product on average). "Top Produtos por
  Receita" reflects a real, non-flat distribution (top product here
  is ~3M in revenue against a long tail), not an artifact.
- **"Pedidos por Dia" covers only 3 real days** (2026-08-01 to
  2026-08-03 — this is genuinely all the data the simulator has
  generated so far, not a query bug). The daily volume itself is a
  real, steep ramp-up (1,000 → 12,149 → 124,058 orders/day), not
  flat — but a 3-point chart is still a 3-point chart. No date-range
  dashboard filter was added for this reason: filtering a 3-day
  window doesn't add anything yet. **Open question, not decided
  here**: whether a bar chart is still the best visualization for 3
  points, or whether something simpler (e.g. 3 scalars, or a table)
  would communicate this better until there's enough daily history
  for a real trend line — left as a bar chart for now since changing
  chart family is a bigger call than the formatting/layout work this
  pass covered. Revisit alongside the day-vs-month granularity
  question once the simulator has run longer.

## Why `int_order_items_enriched` is `materialized='table'`

The only one of the 4 Gold models that isn't a plain `fact_`/`dim_`,
originally left as a `view` (see `dbt/models/gold/schema.yml`).
Building questions 3 and 4 above against it as a view failed with a
real IAM error:

```
Failed analyzing stored view 'awsdatacatalog.mdp_gold_dev.int_order_items_enriched':
User: mdp-bi-reader-dev is not authorized to perform: glue:GetDatabase
on resource: arn:aws:glue:...:database/mdp_silver_dev
```

A view has to resolve everything it references at query time —
`int_order_items_enriched` joins several `stg_*` models, which live in
`mdp_silver_dev`, outside the BI Reader IAM policy's scope (Gold only,
deliberately — see `docs/architecture/roadmap-next-steps.md`). Rather
than widen that policy to cover all of Silver (a real boundary change,
not a Metabase-only one), the model was changed to
`materialized='table'` with an explicit `external_location`, matching
`dim_customers`/`dim_products`/`fact_orders` — it now has its own
physical copy under `gold/mdp_gold_dev/int_order_items_enriched/` and
no runtime dependency on Silver at query time.

## Formatting, titles, and layout — what worked via the API vs what didn't

Everything below was attempted via the API first, per this project's
own versioning discipline (SQL/config as text, not manual UI clicks
that leave no diff). Confirmed by reading each setting back
(`GET`/re-fetch), not just trusting a `200` on the `PUT`:

- **Number formatting** (`visualization_settings.column_settings`,
  keyed by `["name","<column>"]`): applied `number_style: "currency"`
  + `currency: "BRL"` to `revenue` (card 42) and `average_order_value`
  (card 44); `number_style: "decimal"` with Brazilian separators
  (`number_separators: ".,"`) to `total_orders` (card 40). Confirmed
  the settings persist via `GET /api/card/:id`; actual pixel rendering
  (does `R$ 3.010.485,66` really show up in the UI) was **not**
  visually confirmed — this API can save the setting but can't
  screenshot the rendered chart.
- **`column_title`** (per-column, inside the same `column_settings`
  entries): set on every displayed column across all 5 cards (e.g.
  `total_orders` → "Total de Pedidos", `product_name` → "Produto").
  Same caveat as above — persisted, not visually confirmed.
- **Horizontal bars for cards 42/43**: used `display: "row"`, a
  distinct Metabase chart type for horizontal bars — not a
  `graph.orientation` setting on `display: "bar"` (that setting either
  doesn't exist in this version's schema or isn't the documented
  mechanism; `row` is). Confirmed each card still executes correctly
  under the new display type (`POST /api/card/:id/query`).
- **Instance color palette (`application-colors` setting)**:
  confirmed the setting key exists (`GET /api/setting`), but `PUT
  /api/setting/application-colors` returned a real `500` with an
  explicit reason: *"Setting application-colors is not enabled
  because feature :whitelabel is not available"*. This is a
  Pro/Enterprise-gated feature (whitelabeling), not merely
  API-restricted — the Admin → Appearance color pickers in the UI are
  almost certainly gated behind the same feature flag on this
  open-source install, so this is likely **not achievable at all**
  on this edition, not just "needs the UI instead of the API".
  **Not simulated or worked around** — reported as-is, per this
  project's convention of not gambiarra-ing around a real permission
  boundary.
- **Dashboard layout** (`PUT /api/dashboard/:id`, `dashcards` array):
  reorganized into the layout described above. Assumed a 24-unit-wide
  grid (common in recent Metabase versions) to place the two `row`
  charts side by side at `size_x: 12` each — **not visually confirmed
  that 10 category labels (product/seller names) stay legible at
  half-width**; worth checking in the UI and widening back to
  full-width stacked (`size_x: 24` each, one above the other) if they
  look cramped.

## Recreating this dashboard from scratch (Serialization isn't available)

If Metabase is ever recreated (a fresh `postgres-metabase` volume, a
new environment, etc.), there's no one-command import — do this via
the API, same as it was built:

1. **Authenticate**: `POST /api/session` with the admin
   email/password (or `POST /api/setup` first, if this is a genuinely
   fresh instance — see the Sprint 12 investigation notes in
   `docs/architecture/roadmap-next-steps.md` for the full first-boot
   flow). Use the returned session id as `X-Metabase-Session` on every
   call below.
2. **Confirm the Athena database connection exists** (`GET
   /api/database`) — engine `athena`, workgroup `mdp-athena-dev`,
   schema `mdp_gold_dev`, credentials from the `mdp-bi-reader-dev` IAM
   User (Terraform `module.bi_reader`). Re-create via `POST
   /api/database` if not (see the Sprint 12 notes for the exact
   payload shape).
3. **Re-create each question**: for each `NN_name.sql` file in this
   directory, `POST /api/card` with:
   ```json
   {
     "name": "<Question name, from the table above>",
     "description": "<see the corresponding PUT payload/git history for the exact text>",
     "dataset_query": {
       "type": "native",
       "native": {"query": "<the file's contents, verbatim>"},
       "database": <the database id from step 2>
     },
     "display": "<scalar|bar|row, from the table above>",
     "visualization_settings": {"...": "see git history for the exact column_settings/graph.dimensions payload per card"}
   }
   ```
   Record the returned `id` for each.
4. **Re-create the dashboard**: `POST /api/dashboard` with a `name`,
   then `PUT /api/dashboard/:id` with a `dashcards` array (one entry
   per question, negative placeholder `id`s, `card_id` from step 3,
   and `row`/`col`/`size_x`/`size_y` for layout — see this session's
   real payloads in git history for exact values).
5. **Sanity-check every card actually runs** (`POST
   /api/card/:id/query`) before considering it done — a `POST
   /api/card` that succeeds only means the SQL parsed, not that it can
   execute under the BI Reader's IAM policy (see the
   `int_order_items_enriched` caveat above — this exact failure mode
   is why this step exists).
6. **Instance-wide appearance (color palette) cannot be scripted on
   this edition** — see the caveat above. Skip it; it's gated behind
   a Pro/Enterprise feature flag (`:whitelabel`), not a missing script.
