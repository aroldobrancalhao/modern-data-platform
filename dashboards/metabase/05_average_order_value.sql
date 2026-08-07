-- Average Order Value
--
-- Simple average of fact_orders.total_amount. No reuse-cardinality
-- caveat applies here -- it's an aggregate over the order amounts
-- themselves, not a count grouped by a low-cardinality-reuse
-- dimension like customer or product.

select avg(total_amount) as average_order_value
from fact_orders
