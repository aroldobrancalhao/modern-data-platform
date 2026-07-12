-- ============================================================================
-- Modern Data Platform
-- Reviews
-- ============================================================================

SET search_path TO marketplace;

-- ============================================================================
-- Reviews
-- ============================================================================

CREATE TABLE reviews
(
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,

    customer_id UUID NOT NULL,

    product_id UUID NOT NULL,

    rating SMALLINT NOT NULL,

    title VARCHAR(200),

    comment TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_reviews_order_product
        UNIQUE
        (
            order_id,
            product_id
        ),

    CONSTRAINT fk_reviews_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_reviews_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_reviews_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_reviews_rating
        CHECK
        (
            rating BETWEEN 1 AND 5
        )
);

COMMENT ON TABLE reviews IS 'Customer product reviews';