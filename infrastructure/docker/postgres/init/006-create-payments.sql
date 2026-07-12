-- ============================================================================
-- Modern Data Platform
-- Payments
-- ============================================================================

SET search_path TO marketplace;

-- ============================================================================
-- Payment Methods
-- ============================================================================

CREATE TABLE payment_methods
(
    payment_method_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    code VARCHAR(30) NOT NULL,
    name VARCHAR(100) NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_payment_methods_code
        UNIQUE (code)
);

COMMENT ON TABLE payment_methods IS 'Available payment methods';

-- ============================================================================
-- Payments
-- ============================================================================

CREATE TABLE payments
(
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    order_id UUID NOT NULL,

    payment_method_id UUID NOT NULL,

    transaction_code VARCHAR(100) NOT NULL,

    amount NUMERIC(19,4) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    authorized_at TIMESTAMPTZ,

    paid_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_payments_order
        UNIQUE (order_id),

    CONSTRAINT uq_payments_transaction
        UNIQUE (transaction_code),

    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_payments_payment_method
        FOREIGN KEY (payment_method_id)
        REFERENCES payment_methods(payment_method_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_payments_amount
        CHECK (amount >= 0),

    CONSTRAINT chk_payments_status
        CHECK
        (
            status IN
            (
                'PENDING',
                'AUTHORIZED',
                'PAID',
                'FAILED',
                'CANCELLED',
                'REFUNDED'
            )
        )
);

COMMENT ON TABLE payments IS 'Order payments';

-- ============================================================================
-- Refunds
-- ============================================================================

CREATE TABLE refunds
(
    refund_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    payment_id UUID NOT NULL,

    amount NUMERIC(19,4) NOT NULL,

    reason VARCHAR(255),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_refunds_payment
        FOREIGN KEY (payment_id)
        REFERENCES payments(payment_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_refunds_amount
        CHECK (amount >= 0)
);

COMMENT ON TABLE refunds IS 'Payment refunds';