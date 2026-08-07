-- Grain: one row per order_item (same grain as stg_order_items).
-- Left joins throughout, even though no orphans exist in the current
-- data (checked against real Athena before writing this model): the
-- 7 Silver entities are extracted independently, at different times,
-- with no atomic snapshot across them, so referential drift between
-- them is a real possibility going forward, not just a theoretical
-- one. A left join keeps this model's grain guaranteed to match
-- stg_order_items regardless; the relationships tests in schema.yml
-- are what should catch any future orphan, not a silently
-- row-dropping inner join.
--
-- materialized='table' (was 'view'): found live querying this model
-- from Metabase -- as a view, Athena has to resolve stg_order_items/
-- stg_orders/stg_products/stg_sellers/stg_categories at query time,
-- which live in mdp_silver_dev, outside the BI Reader IAM policy's
-- scope (Gold only, deliberately -- see docs/architecture/
-- roadmap-next-steps.md). Materializing as a table removes the
-- runtime dependency on Silver entirely, matching dim_customers/
-- dim_products/fact_orders. external_location explicit for the same
-- reason as those three (see dim_customers.sql).

{{ config(
    materialized='table',
    external_location='s3://mdp-datalake-dev-857854758128/gold/mdp_gold_dev/int_order_items_enriched/'
) }}

select
    oi.order_item_id,
    oi.order_id,
    oi.product_id,
    oi.quantity,
    oi.unit_price,
    oi.total_price,
    oi.created_at as order_item_created_at,

    o.order_number,
    o.status as order_status,
    o.customer_id,

    p.name as product_name,
    p.sku as product_sku,
    p.price as product_price,
    p.category_id,
    p.seller_id,

    s.company_name as seller_name,

    c.name as category_name

from {{ ref('stg_order_items') }} as oi

left join {{ ref('stg_orders') }} as o
    on oi.order_id = o.order_id

left join {{ ref('stg_products') }} as p
    on oi.product_id = p.product_id

left join {{ ref('stg_sellers') }} as s
    on p.seller_id = s.seller_id

left join {{ ref('stg_categories') }} as c
    on p.category_id = c.category_id
