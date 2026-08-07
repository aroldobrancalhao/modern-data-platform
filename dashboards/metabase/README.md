# Metabase — Gold Layer Overview

First real dashboard built on top of the Gold layer, via Metabase
connected to Athena (see `docs/architecture/roadmap-next-steps.md` for
the IAM/location work that made this connection possible). Built via
the Metabase API (`POST /api/card`, `PUT /api/dashboard/:id`), not the
visual query builder — every question here is **Native Query (SQL)**,
not the GUI builder, specifically so it stays versionable as plain
text in this directory instead of living only inside Metabase's own
Postgres metadata database.

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
| 1 | `01_total_orders.sql` | Total Orders | 40 | scalar |
| 2 | `02_orders_by_month.sql` | Orders by Month | 41 | bar |
| 3 | `03_top_products_by_revenue.sql` | Top Products by Revenue | 42 | bar |
| 4 | `04_top_sellers_by_orders.sql` | Top Sellers by Order Count | 43 | bar |
| 5 | `05_average_order_value.sql` | Average Order Value | 44 | scalar |

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
  "Top Sellers by Order Count": average ~5.7 distinct orders/seller,
  top seller at 295 — checked with `count(distinct order_id)`, not
  `count(*)`, since one order can carry multiple line items from the
  same seller.
- **Products, by contrast, do show real reuse at the line-item
  level**: 40,113 distinct `product_id` across 137,207 order-item
  rows (~3.4 line items/product on average). "Top Products by
  Revenue" reflects a real, non-flat distribution (top product here
  is ~3M in revenue against a long tail), not an artifact.

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
     "dataset_query": {
       "type": "native",
       "native": {"query": "<the file's contents, verbatim>"},
       "database": <the database id from step 2>
     },
     "display": "<scalar|bar, from the table above>",
     "visualization_settings": {}
   }
   ```
   Record the returned `id` for each.
4. **Re-create the dashboard**: `POST /api/dashboard` with a `name`,
   then `PUT /api/dashboard/:id` with a `dashcards` array (one entry
   per question, negative placeholder `id`s, `card_id` from step 3,
   and `row`/`col`/`size_x`/`size_y` for layout — see this session's
   real payload in git history for exact values, commit that added
   this README).
5. **Sanity-check every card actually runs** (`POST
   /api/card/:id/query`) before considering it done — a `POST
   /api/card` that succeeds only means the SQL parsed, not that it can
   execute under the BI Reader's IAM policy (see the
   `int_order_items_enriched` caveat above — this exact failure mode
   is why this step exists).
