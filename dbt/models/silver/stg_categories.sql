select
    cast(category_id as varchar) as category_id,
    cast(parent_category_id as varchar) as parent_category_id,
    cast(name as varchar) as name,
    cast(description as varchar) as description,
    cast(is_active as boolean) as is_active,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at,
    cast(processed_at as timestamp) as processed_at,
    cast(processing_date as date) as processing_date

from {{ source('silver', 'categories') }}
