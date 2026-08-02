select
    cast(customer_id as varchar) as customer_id,
    cast(first_name as varchar) as first_name,
    cast(last_name as varchar) as last_name,
    cast(email as varchar) as email,
    cast(phone_number as varchar) as phone_number,
    cast(document_number as varchar) as document_number,
    cast(birth_date as date) as birth_date,
    cast(is_active as boolean) as is_active,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at,
    cast(deleted_at as timestamp) as deleted_at,
    cast(processed_at as timestamp) as processed_at,
    cast(processing_date as date) as processing_date

from {{ source('silver', 'customers') }}
