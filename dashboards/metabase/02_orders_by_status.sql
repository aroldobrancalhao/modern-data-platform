-- Orders by Status
--
-- Replaces Orders by Day (see git history for that version). "Pedidos
-- por Dia" stopped being a useful chart once the org-status trickle
-- landed: the day axis was still frozen at the same 3-day
-- (2026-08-01 to 2026-08-03) bulk-insert ramp-up, unrelated to the
-- thing actually worth showing now.
--
-- order_status has real variation as of 2026-08-13 -- was cardinality
-- 1 (only PENDING) when this dashboard was first built (see this
-- directory's git history), unblocked by
-- src/simulator/domain/orders/order_status_service.py's organic
-- trickle plus scripts/backfill_order_status.py's one-time seed of
-- the pre-existing backlog (see docs/architecture/roadmap-next-steps.md,
-- "Simulator -- order status progression engine"). Confirmed live
-- end to end before building this, not assumed: 21 real
-- PENDING -> PAID/CANCELLED transitions observed during a 2026-08-13
-- trickle validation run, each with a matching Debezium/Kafka UPDATE
-- event (op="u") -- the first proof this schema had of CDC carrying
-- an UPDATE, not just INSERT.
--
-- status_order: forces the funnel-then-terminal display order
-- (PENDING -> PAID -> PROCESSING -> SHIPPED, then the two terminal
-- states DELIVERED/CANCELLED) instead of Metabase's default
-- alphabetical dimension ordering, which would interleave them
-- (CANCELLED, DELIVERED, PAID, PENDING, PROCESSING, SHIPPED) and
-- break both the funnel reading and the color story (see this
-- directory's README -- ordinal ramp for the 4 in-flight stages,
-- fixed status colors for the 2 terminal ones). Same
-- sort-column-plus-display-column pattern the old orders-by-day
-- version used (order_day + period).

select
    order_status,
    count(*) as total_orders,
    case order_status
        when 'PENDING'    then 1
        when 'PAID'       then 2
        when 'PROCESSING' then 3
        when 'SHIPPED'    then 4
        when 'DELIVERED'  then 5
        when 'CANCELLED'  then 6
    end as status_order
from fact_orders
group by order_status
order by status_order
