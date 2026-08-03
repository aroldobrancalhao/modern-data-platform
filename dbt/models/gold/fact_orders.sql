-- Grain: one row per order (not order_item -- see
-- int_order_items_enriched for the line-item grain). order_items is
-- pre-aggregated to order level (item_count, total_quantity) before
-- joining, so it can't fan out this fact's grain; payments joins 1:1
-- by construction (uq_payments_order in the source schema, at most
-- one payment per order) so it's safe to join directly without
-- aggregating. order_status_category (a second business rule beyond
-- the raw status passthrough) was considered and dropped, same as
-- noted in docs/architecture/roadmap-next-steps.md: orders.status has
-- cardinality 1 in the real data today (only PENDING), so there is no
-- real variation yet to encode a rule against. order_value_tier
-- (ntile(3) over total_amount) is the one business rule that survived
-- that same pass -- the only real, data-backed rule available today.
-- Natural key (order_id), no surrogate -- same reasoning as
-- dim_customers/dim_products.
--
-- materialized='table', partitioned_by=['order_year', 'order_month']:
-- final-layer fact benefits from physical materialization (unlike
-- stg_/int_, which stay view by staging convention), and a real
-- partition on real volume is a deliberate choice to demonstrate one.
-- order_year/order_month are last in the select list on purpose --
-- Athena's Hive CTAS requires partition columns to be the trailing
-- columns of the query, in the order declared in partitioned_by.

{{ config(
    materialized='table',
    partitioned_by=['order_year', 'order_month']
) }}

with order_item_aggregates as (
    select
        order_id,
        count(*) as item_count,
        sum(quantity) as total_quantity

    from {{ ref('stg_order_items') }}

    group by order_id
)

select
    o.order_id,
    o.order_number,
    o.customer_id,
    o.status as order_status,
    o.total_amount,
    o.shipping_amount,
    o.created_at,
    o.updated_at,

    coalesce(oia.item_count, 0) as item_count,
    coalesce(oia.total_quantity, 0) as total_quantity,

    p.payment_id,
    p.status as payment_status,
    p.payment_method_id,
    p.paid_at,

    ntile(3) over (order by o.total_amount) as order_value_tier,

    year(o.created_at) as order_year,
    month(o.created_at) as order_month

from {{ ref('stg_orders') }} as o

left join order_item_aggregates as oia
    on o.order_id = oia.order_id

left join {{ ref('stg_payments') }} as p
    on o.order_id = p.order_id
