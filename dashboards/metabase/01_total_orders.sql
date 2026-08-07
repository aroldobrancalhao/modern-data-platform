-- Total Orders
--
-- Simple count of every order in the Gold layer. No caveats -- order
-- count itself is real, simulator-generated volume, not affected by
-- the customer/product 1:1-reuse pattern noted elsewhere in this
-- directory's README.

select count(*) as total_orders
from fact_orders
