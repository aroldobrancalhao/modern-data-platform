select
    cast(product_id as varchar) as product_id,
    cast(seller_id as varchar) as seller_id,
    cast(category_id as varchar) as category_id,
    cast(sku as varchar) as sku,
    cast(name as varchar) as name,
    cast(description as varchar) as description,
    cast(brand as varchar) as brand,
    cast(price as decimal(19, 4)) as price,
    cast(weight as decimal(10, 3)) as weight,
    cast(height as decimal(10, 2)) as height,
    cast(width as decimal(10, 2)) as width,
    cast(length as decimal(10, 2)) as length,
    cast(status as varchar) as status,
    cast(is_active as boolean) as is_active,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at,
    cast(deleted_at as timestamp) as deleted_at,
    cast(processed_at as timestamp) as processed_at,
    cast(processing_date as date) as processing_date

from {{ source('silver', 'products') }}
