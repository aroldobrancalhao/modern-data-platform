-- Orders by Day
--
-- Originally grouped by fact_orders' own order_year/order_month
-- partition columns (month granularity). Switched to day granularity
-- using date_trunc('day', created_at) -- confirmed against real
-- Athena (Trino engine) before assuming the syntax: date_trunc('day',
-- <timestamp>) is valid and returns a truncated timestamp. There is
-- no order_day partition column on fact_orders to reuse the way
-- order_year/order_month were reused for the month version, so this
-- derives it from created_at directly instead.
--
-- Caveat (see this directory's README): the simulator has only
-- generated 3 distinct days of data so far (2026-08-01 to
-- 2026-08-03), with a steep ramp-up (1,000 -> 12,149 -> 124,058
-- orders/day) -- real variation, not a bug, but a 3-point chart. No
-- date-range dashboard filter was added for this reason: filtering a
-- 3-day window doesn't add anything yet. Revisit (both the chart type
-- and whether a filter is worth adding) once the simulator has
-- generated enough days for a real trend line to make sense.

select
    date_trunc('day', created_at) as order_day,
    cast(date_trunc('day', created_at) as varchar) as period,
    count(*) as total_orders
from fact_orders
group by date_trunc('day', created_at)
order by order_day
