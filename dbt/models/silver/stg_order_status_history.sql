select
    cast(history_id as varchar) as history_id,
    cast(order_id as varchar) as order_id,
    cast(previous_status as varchar) as previous_status,
    cast(current_status as varchar) as current_status,
    cast(changed_at as timestamp) as changed_at,
    cast(processed_at as timestamp) as processed_at,
    cast(processing_date as date) as processing_date

from {{ source('silver', 'order_status_history') }}
