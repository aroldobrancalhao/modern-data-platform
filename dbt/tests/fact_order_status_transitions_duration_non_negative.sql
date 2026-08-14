-- duration_in_previous_status_seconds is a time diff (lag(changed_at)
-- per order, falling back to stg_orders.created_at on the genesis
-- row) -- should never go negative under correctly-ordered
-- timestamps. Fails (returns rows) if it ever does.

select *

from {{ ref('fact_order_status_transitions') }}

where duration_in_previous_status_seconds < 0
