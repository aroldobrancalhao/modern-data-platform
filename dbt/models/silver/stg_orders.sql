select
    cast(order_id as varchar) as order_id,
    cast(order_number as varchar) as order_number,
    cast(customer_id as varchar) as customer_id,
    cast(status as varchar) as status,
    cast(total_amount as decimal(19, 4)) as total_amount,
    cast(shipping_amount as decimal(19, 4)) as shipping_amount,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at,
    cast(processed_at as timestamp) as processed_at,
    cast(processing_date as date) as processing_date

from {{ source('silver', 'orders') }}
