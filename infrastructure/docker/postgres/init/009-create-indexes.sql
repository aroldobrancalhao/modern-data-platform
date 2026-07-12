-- ============================================================================
-- Modern Data Platform
-- Indexes
-- ============================================================================

SET search_path TO marketplace;

-- ============================================================================
-- Customers
-- ============================================================================

CREATE INDEX idx_customers_created_at
    ON customers(created_at);

CREATE INDEX idx_customers_updated_at
    ON customers(updated_at);

-- ============================================================================
-- Customer Addresses
-- ============================================================================

CREATE INDEX idx_customer_addresses_customer_id
    ON customer_addresses(customer_id);

-- ============================================================================
-- Sellers
-- ============================================================================

CREATE INDEX idx_sellers_created_at
    ON sellers(created_at);

CREATE INDEX idx_sellers_updated_at
    ON sellers(updated_at);

-- ============================================================================
-- Categories
-- ============================================================================

CREATE INDEX idx_categories_parent_category_id
    ON categories(parent_category_id);

-- ============================================================================
-- Products
-- ============================================================================

CREATE INDEX idx_products_seller_id
    ON products(seller_id);

CREATE INDEX idx_products_category_id
    ON products(category_id);

CREATE INDEX idx_products_status
    ON products(status);

CREATE INDEX idx_products_created_at
    ON products(created_at);

-- ============================================================================
-- Warehouses
-- ============================================================================

CREATE INDEX idx_warehouses_created_at
    ON warehouses(created_at);

-- ============================================================================
-- Inventories
-- ============================================================================

CREATE INDEX idx_inventories_product_id
    ON inventories(product_id);

CREATE INDEX idx_inventories_warehouse_id
    ON inventories(warehouse_id);

-- ============================================================================
-- Inventory Movements
-- ============================================================================

CREATE INDEX idx_inventory_movements_inventory_id
    ON inventory_movements(inventory_id);

CREATE INDEX idx_inventory_movements_order_id
    ON inventory_movements(order_id);

CREATE INDEX idx_inventory_movements_created_at
    ON inventory_movements(created_at);

CREATE INDEX idx_inventory_movements_type
    ON inventory_movements(movement_type);

-- ============================================================================
-- Orders
-- ============================================================================

CREATE INDEX idx_orders_customer_id
    ON orders(customer_id);
    
CREATE INDEX idx_orders_status
    ON orders(status);

CREATE INDEX idx_orders_created_at
    ON orders(created_at);

CREATE INDEX idx_orders_updated_at
    ON orders(updated_at);

-- ============================================================================
-- Order Items
-- ============================================================================

CREATE INDEX idx_order_items_order_id
    ON order_items(order_id);

CREATE INDEX idx_order_items_product_id
    ON order_items(product_id);

-- ============================================================================
-- Order Status History
-- ============================================================================

CREATE INDEX idx_order_status_history_order_id
    ON order_status_history(order_id);

CREATE INDEX idx_order_status_history_changed_at
    ON order_status_history(changed_at);

-- ============================================================================
-- Payments
-- ============================================================================

CREATE INDEX idx_payments_order_id
    ON payments(order_id);

CREATE INDEX idx_payments_payment_method_id
    ON payments(payment_method_id);

CREATE INDEX idx_payments_status
    ON payments(status);

CREATE INDEX idx_payments_created_at
    ON payments(created_at);

CREATE INDEX idx_payments_paid_at
    ON payments(paid_at);

-- ============================================================================
-- Refunds
-- ============================================================================

CREATE INDEX idx_refunds_payment_id
    ON refunds(payment_id);

CREATE INDEX idx_refunds_created_at
    ON refunds(created_at);

-- ============================================================================
-- Shipments
-- ============================================================================

CREATE INDEX idx_shipments_order_id
    ON shipments(order_id);

CREATE INDEX idx_shipments_carrier_id
    ON shipments(carrier_id);

CREATE INDEX idx_shipments_status
    ON shipments(status);

CREATE INDEX idx_shipments_created_at
    ON shipments(created_at);

CREATE INDEX idx_shipments_delivered_at
    ON shipments(delivered_at);

-- ============================================================================
-- Reviews
-- ============================================================================

CREATE INDEX idx_reviews_customer_id
    ON reviews(customer_id);

CREATE INDEX idx_reviews_product_id
    ON reviews(product_id);

CREATE INDEX idx_reviews_created_at
    ON reviews(created_at);