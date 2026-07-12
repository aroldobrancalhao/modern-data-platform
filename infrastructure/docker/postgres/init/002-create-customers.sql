-- ============================================================================
-- Modern Data Platform
-- Customers
-- ============================================================================

SET search_path TO marketplace;

-- ============================================================================
-- Customers
-- ============================================================================

CREATE TABLE customers
(
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,

    email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),

    document_number VARCHAR(20) NOT NULL,

    birth_date DATE,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT uq_customers_email
        UNIQUE (email),

    CONSTRAINT uq_customers_document_number
        UNIQUE (document_number),

    CONSTRAINT chk_customers_email
        CHECK (position('@' IN email) > 1)
);

COMMENT ON TABLE customers IS 'Marketplace customers';

COMMENT ON COLUMN customers.customer_id IS 'Customer unique identifier';
COMMENT ON COLUMN customers.document_number IS 'CPF or equivalent identification';
COMMENT ON COLUMN customers.deleted_at IS 'Soft delete timestamp';

-- ============================================================================
-- Customer Addresses
-- ============================================================================

CREATE TABLE customer_addresses
(
    address_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    customer_id UUID NOT NULL,

    address_type VARCHAR(20) NOT NULL,

    street VARCHAR(255) NOT NULL,
    street_number VARCHAR(20) NOT NULL,

    complement VARCHAR(255),

    district VARCHAR(150),

    city VARCHAR(150) NOT NULL,

    state VARCHAR(100) NOT NULL,

    country VARCHAR(100) NOT NULL DEFAULT 'Brazil',

    postal_code VARCHAR(20) NOT NULL,

    is_default BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_customer_addresses_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_customer_addresses_type
        CHECK (
            address_type IN (
                'HOME',
                'WORK',
                'DELIVERY',
                'BILLING'
            )
        )
);

COMMENT ON TABLE customer_addresses IS 'Customer addresses';

COMMENT ON COLUMN customer_addresses.address_type IS 'Address classification';
