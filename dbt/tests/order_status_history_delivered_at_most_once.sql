-- fact_orders.delivered_dates assumes DELIVERED is a terminal state
-- (no order ever gets more than one DELIVERED history row) --
-- supported by order_status_service.py (DELIVERED is never a key in
-- _FORWARD_RULES or _CANCEL_PROBABILITY, so no code path transitions
-- away from it), but that's app-code evidence, not data evidence.
-- This is the data-side check: fails (returns rows) if any order
-- ever has more than one.

select
    order_id,
    count(*) as delivered_count

from {{ ref('stg_order_status_history') }}

where current_status = 'DELIVERED'

group by order_id

having count(*) > 1
