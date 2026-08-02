select
    cast(seller_id as varchar) as seller_id,
    cast(company_name as varchar) as company_name,
    cast(trade_name as varchar) as trade_name,
    cast(document_number as varchar) as document_number,
    cast(email as varchar) as email,
    cast(phone_number as varchar) as phone_number,
    cast(is_active as boolean) as is_active,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at,
    cast(deleted_at as timestamp) as deleted_at,
    cast(processed_at as timestamp) as processed_at,
    cast(processing_date as date) as processing_date

from {{ source('silver', 'sellers') }}
