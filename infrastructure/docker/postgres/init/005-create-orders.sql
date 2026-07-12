-- ============================================================================
-- Modern Data Platform
-- Orders
-- ============================================================================

SET search_path TO marketplace;

-- ============================================================================
-- Orders
-- ============================================================================

CREATE TABLE orders
(
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_number VARCHAR(30) NOT NULL,

    customer_id UUID NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    total_amount NUMERIC(19,4) NOT NULL,

    shipping_amount NUMERIC(19,4) NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_orders_order_number
        UNIQUE (order_number),

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_orders_total
        CHECK (total_amount >= 0),

    CONSTRAINT chk_orders_shipping
        CHECK (shipping_amount >= 0),

    CONSTRAINT chk_orders_status
        CHECK
        (
            status IN
            (
                'PENDING',
                'PAID',
                'PROCESSING',
                'SHIPPED',
                'DELIVERED',
                'CANCELLED'
            )
        )
);

COMMENT ON TABLE orders IS 'Marketplace orders';

-- ============================================================================
-- Order Items
-- ============================================================================

CREATE TABLE order_items
(
    order_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,

    product_id UUID NOT NULL,

    quantity INTEGER NOT NULL,

    unit_price NUMERIC(19,4) NOT NULL,

    total_price NUMERIC(19,4) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_order_items_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_order_items_unit_price
        CHECK (unit_price >= 0),

    CONSTRAINT chk_order_items_total
        CHECK (total_price >= 0)
);

COMMENT ON TABLE order_items IS 'Products purchased in each order';

-- ============================================================================
-- Order Status History
-- ============================================================================

CREATE TABLE order_status_history
(
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,

    previous_status VARCHAR(20),

    current_status VARCHAR(20) NOT NULL,

    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_order_status_history_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE order_status_history IS 'Order status change history';

-- ============================================================================
-- Inventory Relationship
-- ============================================================================

ALTER TABLE inventory_movements
ADD COLUMN order_id UUID;

ALTER TABLE inventory_movements
ADD CONSTRAINT fk_inventory_movements_order
FOREIGN KEY (order_id)
REFERENCES orders(order_id)
ON DELETE SET NULL;