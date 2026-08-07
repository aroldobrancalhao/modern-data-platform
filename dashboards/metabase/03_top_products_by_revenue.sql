-- Top Products by Revenue
--
-- Uses int_order_items_enriched (already joins order_items to
-- products) rather than re-joining fact_orders + dim_products from
-- scratch. Checked before building this: 40,113 distinct product_id
-- across 137,207 order_item rows (~3.4 line items/product on
-- average) -- real reuse, real revenue variation (top product here is
-- ~3M vs a long tail), unlike the customer/product 1:1 pattern this
-- directory's README calls out elsewhere.

select
    product_id,
    product_name,
    sum(total_price) as revenue,
    count(*) as line_items
from int_order_items_enriched
group by product_id, product_name
order by revenue desc
limit 15
