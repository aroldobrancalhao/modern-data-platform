select
    cast(payment_id as varchar) as payment_id,
    cast(order_id as varchar) as order_id,
    cast(payment_method_id as varchar) as payment_method_id,
    cast(transaction_code as varchar) as transaction_code,
    cast(amount as decimal(19, 4)) as amount,
    cast(status as varchar) as status,
    cast(authorized_at as timestamp) as authorized_at,
    cast(paid_at as timestamp) as paid_at,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at,
    cast(processed_at as timestamp) as processed_at,
    cast(processing_date as date) as processing_date

from {{ source('silver', 'payments') }}
