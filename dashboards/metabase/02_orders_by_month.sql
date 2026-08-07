-- Orders by Month
--
-- Uses fact_orders' own order_year/order_month partition columns
-- directly (no need to re-derive from created_at) -- real dates,
-- real month-to-month distribution, not a flat/degenerate metric.

select
    order_year,
    order_month,
    cast(order_year as varchar) || '-' || lpad(cast(order_month as varchar), 2, '0') as period,
    count(*) as total_orders
from fact_orders
group by order_year, order_month
order by order_year, order_month
