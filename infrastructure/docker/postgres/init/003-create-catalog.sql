-- ============================================================================
-- Modern Data Platform
-- Catalog
-- ============================================================================

SET search_path TO marketplace;

-- ============================================================================
-- Sellers
-- ============================================================================

CREATE TABLE sellers
(
    seller_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    company_name VARCHAR(255) NOT NULL,
    trade_name VARCHAR(255),

    document_number VARCHAR(20) NOT NULL,

    email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT uq_sellers_document
        UNIQUE (document_number),

    CONSTRAINT uq_sellers_email
        UNIQUE (email),

    CONSTRAINT chk_sellers_email
        CHECK (position('@' IN email) > 1)
);

COMMENT ON TABLE sellers IS 'Marketplace sellers';

-- ============================================================================
-- Categories
-- ============================================================================

CREATE TABLE categories
(
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    parent_category_id UUID,

    name VARCHAR(150) NOT NULL,
    description VARCHAR(500),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_categories_parent
        FOREIGN KEY (parent_category_id)
        REFERENCES categories(category_id)
);

COMMENT ON TABLE categories IS 'Product categories';

-- ============================================================================
-- Products
-- ============================================================================

CREATE TABLE products
(
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    seller_id UUID NOT NULL,
    category_id UUID NOT NULL,

    sku VARCHAR(50) NOT NULL,

    name VARCHAR(255) NOT NULL,
    description TEXT,

    brand VARCHAR(100),

    price NUMERIC(19,4) NOT NULL,

    weight NUMERIC(10,3),
    height NUMERIC(10,2),
    width NUMERIC(10,2),
    length NUMERIC(10,2),

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT uq_products_sku
        UNIQUE (sku),

    CONSTRAINT fk_products_seller
        FOREIGN KEY (seller_id)
        REFERENCES sellers(seller_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id)
        REFERENCES categories(category_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_products_price
        CHECK (price >= 0),

    CONSTRAINT chk_products_status
        CHECK (
            status IN (
                'ACTIVE',
                'INACTIVE',
                'OUT_OF_STOCK'
            )
        )
);

COMMENT ON TABLE products IS 'Marketplace products';