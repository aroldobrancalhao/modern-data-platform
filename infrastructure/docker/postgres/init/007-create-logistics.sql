-- ============================================================================
-- Modern Data Platform
-- Logistics
-- ============================================================================

SET search_path TO marketplace;

-- ============================================================================
-- Carriers
-- ============================================================================

CREATE TABLE carriers
(
    carrier_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    code VARCHAR(30) NOT NULL,

    name VARCHAR(150) NOT NULL,

    phone_number VARCHAR(20),

    email VARCHAR(255),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    deleted_at TIMESTAMPTZ,

    CONSTRAINT uq_carriers_code
        UNIQUE (code),

    CONSTRAINT chk_carriers_email
        CHECK (
            email IS NULL
            OR position('@' IN email) > 1
        )
);

COMMENT ON TABLE carriers IS 'Marketplace carriers';

-- ============================================================================
-- Shipments
-- ============================================================================

CREATE TABLE shipments
(
    shipment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,

    carrier_id UUID NOT NULL,

    tracking_code VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'CREATED',

    shipped_at TIMESTAMPTZ,

    estimated_delivery_at TIMESTAMPTZ,

    delivered_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_shipments_tracking_code
        UNIQUE (tracking_code),

    CONSTRAINT fk_shipments_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_shipments_carrier
        FOREIGN KEY (carrier_id)
        REFERENCES carriers(carrier_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_shipments_status
        CHECK
        (
            status IN
            (
                'CREATED',
                'SHIPPED',
                'IN_TRANSIT',
                'DELIVERED',
                'RETURNED'
            )
        )
);

COMMENT ON TABLE shipments IS 'Marketplace shipments';