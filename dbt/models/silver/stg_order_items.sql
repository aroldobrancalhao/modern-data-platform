select
    cast(order_item_id as varchar) as order_item_id,
    cast(order_id as varchar) as order_id,
    cast(product_id as varchar) as product_id,
    cast(quantity as integer) as quantity,
    cast(unit_price as decimal(19, 4)) as unit_price,
    cast(total_price as decimal(19, 4)) as total_price,
    cast(created_at as timestamp) as created_at,
    cast(processed_at as timestamp) as processed_at,
    cast(processing_date as date) as processing_date

from {{ source('silver', 'order_items') }}
