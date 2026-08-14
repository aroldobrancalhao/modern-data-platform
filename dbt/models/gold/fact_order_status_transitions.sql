-- Grain: one row per order_status_history row, i.e. one row per
-- status transition (including the genesis transition every order
-- gets on creation: previous_status is null, current_status =
-- 'PENDING' -- see OrderStatusHistory.create() in the simulator).
-- previous_status is therefore only ever null on that first row per
-- order; every real transition after it always carries the status
-- being left (OrderStatusRepository.transition() always passes a
-- real previous_status).
--
-- duration_in_previous_status_seconds: how long the order sat in
-- previous_status before this transition happened. lag(changed_at)
-- over each order's own history, ordered by changed_at, gives the
-- prior transition's timestamp for every row except the first: for
-- that one (previous_status is null, there is no prior history row)
-- it falls back to stg_orders.created_at, since the genesis row's
-- own "previous state" is the order not existing yet, and created_at
-- is the correct anchor for that duration -- not left null.
--
-- relationships test targets stg_orders, not fact_orders -- same
-- convention as int_order_items_enriched (gold tests against
-- silver-staged data, not against another gold model).
--
-- materialized='table', not partitioned: same BI-access reasoning as
-- int_order_items_enriched (Metabase's BI Reader IAM policy is
-- scoped to Gold only, so a view that resolves stg_order_status_history/
-- stg_orders at query time would reach outside it) -- no partitioning
-- since, unlike fact_orders, there's no established volume yet to
-- partition against.

{{ config(
    materialized='table',
    external_location='s3://mdp-datalake-dev-857854758128/gold/mdp_gold_dev/fact_order_status_transitions/'
) }}

with history as (
    select
        history_id,
        order_id,
        previous_status,
        current_status,
        changed_at,

        lag(changed_at) over (
            partition by order_id
            order by changed_at
        ) as prior_changed_at

    from {{ ref('stg_order_status_history') }}
)

select
    h.history_id,
    h.order_id,
    h.previous_status,
    h.current_status,
    h.changed_at,

    date_diff(
        'second',
        coalesce(h.prior_changed_at, o.created_at),
        h.changed_at
    ) as duration_in_previous_status_seconds

from history as h

left join {{ ref('stg_orders') }} as o
    on h.order_id = o.order_id
