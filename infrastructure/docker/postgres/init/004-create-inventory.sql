-- ============================================================================
-- Modern Data Platform
-- Inventory
-- ============================================================================

SET search_path TO marketplace;

-- ============================================================================
-- Warehouses
-- ============================================================================

CREATE TABLE warehouses
(
    warehouse_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    code VARCHAR(20) NOT NULL,
    name VARCHAR(150) NOT NULL,

    street VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'Brazil',

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT uq_warehouses_code
        UNIQUE (code)
);

COMMENT ON TABLE warehouses IS 'Marketplace warehouses';

-- ============================================================================
-- Inventories
-- ============================================================================

CREATE TABLE inventories
(
    inventory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    warehouse_id UUID NOT NULL,
    product_id UUID NOT NULL,

    available_quantity INTEGER NOT NULL DEFAULT 0,
    reserved_quantity INTEGER NOT NULL DEFAULT 0,
    minimum_quantity INTEGER NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_inventories_warehouse
        FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_inventories_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT uq_inventory_product
        UNIQUE (
            warehouse_id,
            product_id
        ),

    CONSTRAINT chk_inventory_available
        CHECK (available_quantity >= 0),

    CONSTRAINT chk_inventory_reserved
        CHECK (reserved_quantity >= 0),

    CONSTRAINT chk_inventory_minimum
        CHECK (minimum_quantity >= 0)
);

COMMENT ON TABLE inventories IS 'Current inventory per warehouse';

-- ============================================================================
-- Inventory Movements
-- ============================================================================

CREATE TABLE inventory_movements
(
    movement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    inventory_id UUID NOT NULL,

    movement_type VARCHAR(20) NOT NULL,

    quantity INTEGER NOT NULL,

    reason VARCHAR(255),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_inventory_movements_inventory
        FOREIGN KEY (inventory_id)
        REFERENCES inventories(inventory_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_inventory_movement_type
        CHECK (
            movement_type IN
            (
                'INBOUND',
                'OUTBOUND',
                'RESERVATION',
                'RELEASE',
                'ADJUSTMENT'
            )
        ),

    CONSTRAINT chk_inventory_quantity
        CHECK (quantity > 0)
);

COMMENT ON TABLE inventory_movements IS 'Inventory movement history';