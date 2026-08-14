-- delivered_at (when present) should never be earlier than the
-- order's own created_at. Fails (returns rows) if it ever is.

select *

from {{ ref('fact_orders') }}

where delivered_at is not null
  and delivered_at < created_at
