-- Grain: one row per product (same as stg_products), denormalized
-- with seller and category names -- same left-join pattern and
-- rationale as int_order_items_enriched: the 7 Silver entities have
-- no atomic cross-entity snapshot, so a left join keeps this model's
-- grain guaranteed to match stg_products regardless of any
-- referential drift between extracts; the relationships tests in
-- schema.yml are what should catch an orphan, not a silently
-- row-dropping inner join. Natural key (product_id), no surrogate --
-- same reasoning as dim_customers. Plain latest-state dimension, not
-- SCD2, same rationale as dim_customers.
--
-- materialized='table': final-layer dim/fact benefit from physical
-- materialization, unlike stg_/int_ which stay view by staging
-- convention.

{{ config(materialized='table') }}

select
    p.product_id,
    p.seller_id,
    p.category_id,
    p.sku,
    p.name as product_name,
    p.description,
    p.brand,
    p.price,
    p.weight,
    p.height,
    p.width,
    p.length,
    p.status as product_status,
    p.is_active,
    p.created_at,
    p.updated_at,
    p.deleted_at,

    s.company_name as seller_name,
    s.is_active as seller_is_active,

    c.name as category_name

from {{ ref('stg_products') }} as p

left join {{ ref('stg_sellers') }} as s
    on p.seller_id = s.seller_id

left join {{ ref('stg_categories') }} as c
    on p.category_id = c.category_id
