-- Average Delivery Time
--
-- Average hours between an order's created_at and delivered_at,
-- restricted to orders that actually reached DELIVERED
-- (fact_orders.delivered_at is not null). Both columns come from
-- fact_orders directly (delivered_at added alongside
-- fact_order_status_transitions in the order_status_history Fase 4
-- work -- see docs/architecture/roadmap-next-steps.md), no new model
-- needed.
--
-- Real number, checked live before building this card (2026-09-19):
-- 131,069 delivered orders, avg 0.28h, min 0.18h, max 68.31h. The
-- average being ~17 minutes is a simulator-timing artifact, not a
-- realistic logistics figure -- OrderStatusService progresses orders
-- through PENDING -> ... -> DELIVERED on its own organic trickle
-- cadence (capped at 15 orders/status/tick), not real-world shipping
-- time. Kept as-is per this directory's existing convention (see the
-- other data caveats in README.md) -- the number is real and
-- reproducible against the actual data, just not representative of an
-- actual delivery SLA. Same caveat applies to the avg_hours_in_
-- previous_status figures already surfaced per-stage via `dbt show`
-- in the previous session (PENDING 0.0h, PAID 0.05h, PROCESSING
-- 0.08h, SHIPPED 0.1h, DELIVERED 0.13h) -- this card is the funnel
-- total, not a new/different measurement.
--
-- No cancellation-rate model exists on purpose (see
-- docs/architecture/roadmap-next-steps.md) -- final metric
-- aggregation stays in BI, consistent with this dashboard's own
-- pattern (every other scalar/aggregate here is plain SQL against
-- Gold, not a dedicated dbt model per metric).

select
    round(avg(date_diff('second', created_at, delivered_at)) / 3600.0, 2)
        as avg_delivery_hours
from fact_orders
where delivered_at is not null
