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
| 2 | `02_orders_by_status.sql` | Pedidos por Status | 41 | bar |
| 3 | `03_top_products_by_revenue.sql` | Top Produtos por Receita | 42 | row (horizontal bar) |
| 4 | `04_top_sellers_by_orders.sql` | Top Vendedores por Nº de Pedidos | 43 | row (horizontal bar) |
| 5 | `05_average_order_value.sql` | Ticket Médio | 44 | scalar |

**2026-08-13 revision**: replaced "Pedidos por Dia" (card 41) with
"Pedidos por Status" -- see `02_orders_by_status.sql`'s own header for
why, and the "Color palette" section below for the new per-card
colors applied across all 5 cards. Original file kept in git history,
not just discarded (`git log -- dashboards/metabase/02_orders_by_day.sql`).

Layout: the two scalars side by side on top, "Pedidos por Status"
full-width below them, the two `row` charts side by side (2 columns)
at the bottom.

## Data caveats (checked before building, not assumed)

The underlying dataset is simulator-generated, and a few dimensions
don't behave the way a real marketplace's would. Checked the
cardinality of each metric against real Athena data before deciding
whether it was worth building:

- **`order_status` had cardinality 1 when this dashboard was first
  built** (only `PENDING` existed then). No longer true as of
  2026-08-13 — see `02_orders_by_status.sql`'s own header for the
  organic trickle that unblocked it, and the "Color palette" section
  below for how that card is colored. Left here as a dated note, not
  removed outright, since it explains why this dashboard didn't have
  a status breakdown for its first revision.
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
- **"Pedidos por Dia" was replaced, not kept as a second card** — it
  only ever covered 3 real days (2026-08-01 to 2026-08-03, a genuine
  ramp-up, not a query bug), and stayed frozen there regardless of how
  much later data existed, since nothing in the simulator generates
  more distinct days on its own. "Pedidos por Status" replaces it
  because it reflects data that's actually changing now (the org-status
  trickle); the day-vs-month granularity question this caveat used to
  raise is moot without a day-grain card on the dashboard, and can come
  back if a real multi-day trend is ever worth charting again.
- **Every card here reads from `fact_orders`/`int_order_items_enriched`
  in Gold, refreshed only by a manual `marketplace_batch_pipeline`
  run** (`schedule=None` — see `docs/architecture/roadmap-next-steps.md`).
  Numbers on this dashboard are a snapshot as of the last successful
  run, not live against Postgres — confirmed live 2026-08-13: Gold's
  `fact_orders` sat stale at a 2026-08-11 snapshot (137,207 orders)
  through a same-day 138k-order backfill and a ~170-order trickle test,
  because nobody re-ran the pipeline successfully in between (3 manual
  attempts that day failed, all traced to unrelated test scaffolding
  for the `mdp-pipeline-stale` alert, not a real pipeline bug). Not a
  Metabase-side cache or filter issue — re-run the DAG to refresh.

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
  `total_orders` → "Pedidos", `product_name` → "Produto"). Same
  caveat as above — persisted, not visually confirmed.
- **Chart axis titles are a *different* setting from `column_title`**:
  found live -- setting `column_title` alone left the chart axes
  showing raw column names (`total_orders`, `product_name`, ...).
  `column_title` renames a column for tables/tooltips; the actual
  axis label on a bar/row chart is `graph.x_axis.title_text`/
  `graph.y_axis.title_text` (top-level `visualization_settings` keys,
  not nested under `column_settings`). Set on cards 41/42/43 (e.g.
  card 41: x-axis "Dia", y-axis "Pedidos"); confirmed both settings
  persist and every card still executes.
- **Horizontal bars for cards 42/43**: used `display: "row"`, a
  distinct Metabase chart type for horizontal bars — not a
  `graph.orientation` setting on `display: "bar"` (that setting either
  doesn't exist in this version's schema or isn't the documented
  mechanism; `row` is). Confirmed each card still executes correctly
  under the new display type (`POST /api/card/:id/query`).
- **Instance color palette (`application-colors` setting) — confirmed
  genuinely unavailable, not just API-restricted**: `PUT
  /api/setting/application-colors` returned a real `500` both times it
  was tried, with an explicit reason: *"Setting application-colors is
  not enabled because feature :whitelabel is not available"*. Checked
  further before giving up on it: `GET /api/setting/token-features`
  shows every single premium flag as `false` (`whitelabel: false`,
  `serialization: false`, `embedding: false`, ~60 others, all `false`)
  and `enable-whitelabeling?: false` -- this instance has **no license
  token at all**, not a specific restriction on this one setting. The
  Admin → Appearance page's color pickers (Settings gear icon → Admin
  settings → Appearance → "User interface colors" / "Chart colors")
  are almost certainly gated behind the same `:whitelabel` check in
  the UI too, so this is likely not achievable by clicking through the
  UI either on this open-source install -- not merely "needs a human
  instead of the API". **Not simulated or worked around** — reported
  as-is, per this project's convention of not gambiarra-ing around a
  real permission boundary. If this becomes a real requirement later,
  the actual options are a paid Metabase plan, or per-chart
  `series_settings.<key>.color` overrides (a different, narrower
  mechanism -- colors one question's series at a time, not an
  instance-wide theme -- and wasn't asked for here).
- **Dashboard layout** (`PUT /api/dashboard/:id`, `dashcards` array):
  reorganized into the layout described above. Assumed a 24-unit-wide
  grid (common in recent Metabase versions) to place the two `row`
  charts side by side at `size_x: 12` each — **not visually confirmed
  that 10 category labels (product/seller names) stay legible at
  half-width**; worth checking in the UI and widening back to
  full-width stacked (`size_x: 24` each, one above the other) if they
  look cramped.

## Color palette (2026-08-13)

Instance-wide theming is still unavailable (see the "Instance color
palette" note above — unchanged). What's new here is the per-card
`series_settings.<dimension-value>.color` override the note above
already flagged as the real mechanism, applied consistently across
all 5 cards instead of the auto-assigned, no-particular-reason colors
they had before (yellow on card 42, blue on card 43, arrived at by
Metabase's own default rotation, not a choice). Picked via this
project's `dataviz` skill — every hex below is a documented, pre-
validated slot from that skill's reference palette, none invented for
this dashboard.

**Volume vs. financial** — one hue per metric family, applied to every
card of that family:

| Family | Color | Hex | Cards |
|---|---|---|---|
| Volume (counts) | blue (categorical slot 1) | `#2a78d6` | Total de Pedidos (40), Top Vendedores por Nº de Pedidos (43) |
| Financial (R$) | orange (categorical slot 2) | `#eb6834` | Top Produtos por Receita (42), Ticket Médio (44) |

Blue/orange are slots 1 and 2 of the skill's documented 8-hue
categorical order — already validated as an adjacent pair (CVD ΔE 9.1
light / 8.4 dark, above the 8 target), not a new combination.

**Pedidos por Status (card 41)** — modeled as an ordinal ramp for the
4 in-flight stages plus 2 fixed status tokens for the terminal states,
not 6 unrelated categorical colors, because that's what the data
actually is (a funnel with two outcomes):

| Status | Role | Hex |
|---|---|---|
| PENDING | ordinal step 1/4 | `#86b6ef` |
| PAID | ordinal step 2/4 | `#5598e7` |
| PROCESSING | ordinal step 3/4 | `#2a78d6` |
| SHIPPED | ordinal step 4/4 | `#1c5cab` |
| DELIVERED | status "good" (fixed) | `#0ca30c` |
| CANCELLED | status "critical" (fixed) | `#d03b3b` |

The 4 ordinal steps are the skill's documented sequential-blue ramp
(steps 250/350/450/550) — darker means further along, and the ramp
starts at step 250 specifically because the skill's own ordinal rule
requires the lightest step to still clear 2:1 contrast on a white
surface. DELIVERED/CANCELLED deliberately break into a different hue
family (green/red) so a terminal outcome never reads as "just another
stage." Green-vs-red next to each other is the classic red-green CVD
collision; the mitigation here is that they're never color-alone —
`order_status`'s own text label sits on every bar's x-axis position by
construction, not an extra element added for accessibility.

`status_order` (see `02_orders_by_status.sql`) exists so this reads
left-to-right as PENDING → PAID → PROCESSING → SHIPPED → DELIVERED →
CANCELLED, not Metabase's default alphabetical dimension order, which
would scatter the two terminal states apart from each other and break
the ramp's progression reading.

**Not re-validated with the skill's own script in this pass** — `node`
isn't available in the environment this was built in, so the check was
done by construction (every value above is copied from the skill's
already-validated reference table, not a new combination run through
the validator fresh). Worth an actual `validate_palette.js` run
opportunistically if `node` becomes available.

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
   Per-card colors are NOT skipped, though — re-apply the hex values
   from the "Color palette" section above via each card's
   `series_settings` (`PUT /api/card/:id`) once every question is
   re-created.
