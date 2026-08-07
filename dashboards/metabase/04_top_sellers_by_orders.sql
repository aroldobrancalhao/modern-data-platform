-- Top Sellers by Order Count
--
-- Checked before building this one, same discipline as the caveats
-- documented in this directory's README: the sellers table itself has
-- ~137k rows (same order of magnitude as customers/products, i.e. no
-- realistic reuse at the seller-record level), but a seller's
-- *products* can appear across many different orders. Confirmed real
-- variation: 24,243 distinct sellers actually appear in
-- int_order_items_enriched (not ~137k), average ~5.7 distinct orders
-- per seller, top seller at 295 -- a real distribution, not a flat
-- one-order-per-seller artifact.
--
-- count(distinct order_id), not count(*): a single order can contain
-- multiple line items from the same seller, which would otherwise
-- inflate this past the real number of distinct orders reached.

select
    seller_id,
    seller_name,
    count(distinct order_id) as total_orders
from int_order_items_enriched
group by seller_id, seller_name
order by total_orders desc
limit 15
