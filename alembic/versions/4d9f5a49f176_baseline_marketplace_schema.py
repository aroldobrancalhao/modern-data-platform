"""baseline marketplace schema

Adopts Alembic on a database that already has this schema -- the 17
tables were created by infrastructure/docker/postgres/init/*.sql on
first container boot, not by this migration. This migration's
upgrade() is real, complete DDL (captured via `pg_dump --schema-only`
against the real running database) so a genuinely fresh database can
still be bootstrapped with `alembic upgrade head` alone -- but on the
database that already exists today, it is applied via `alembic stamp`
(marks this revision as already-applied without executing the DDL),
never `alembic upgrade`, since the tables are already there.

Deliberately excludes the categories_name_unique constraint (added
this session, after this schema snapshot was taken) -- that is its own
migration, see the next revision.

Revision ID: 4d9f5a49f176
Revises: 
Create Date: 2026-08-03 18:50:45.898051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d9f5a49f176'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA_SQL = """
--
-- PostgreSQL database dump
--


-- Dumped from database version 17.10 (Debian 17.10-1.pgdg13+1)
-- Dumped by pg_dump version 17.10 (Debian 17.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: marketplace; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA marketplace;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: carriers; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.carriers (
    carrier_id uuid DEFAULT gen_random_uuid() NOT NULL,
    code character varying(30) NOT NULL,
    name character varying(150) NOT NULL,
    phone_number character varying(20),
    email character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT chk_carriers_email CHECK (((email IS NULL) OR (POSITION(('@'::text) IN (email)) > 1)))
);


--
-- Name: TABLE carriers; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.carriers IS 'Marketplace carriers';


--
-- Name: categories; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.categories (
    category_id uuid DEFAULT gen_random_uuid() NOT NULL,
    parent_category_id uuid,
    name character varying(150) NOT NULL,
    description character varying(500),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE categories; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.categories IS 'Product categories';


--
-- Name: customer_addresses; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.customer_addresses (
    address_id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id uuid NOT NULL,
    address_type character varying(20) NOT NULL,
    street character varying(255) NOT NULL,
    street_number character varying(20) NOT NULL,
    complement character varying(255),
    district character varying(150),
    city character varying(150) NOT NULL,
    state character varying(100) NOT NULL,
    country character varying(100) DEFAULT 'Brazil'::character varying NOT NULL,
    postal_code character varying(20) NOT NULL,
    is_default boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_customer_addresses_type CHECK (((address_type)::text = ANY ((ARRAY['HOME'::character varying, 'WORK'::character varying, 'DELIVERY'::character varying, 'BILLING'::character varying])::text[])))
);


--
-- Name: TABLE customer_addresses; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.customer_addresses IS 'Customer addresses';


--
-- Name: COLUMN customer_addresses.address_type; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON COLUMN marketplace.customer_addresses.address_type IS 'Address classification';


--
-- Name: customers; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.customers (
    customer_id uuid DEFAULT gen_random_uuid() NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    phone_number character varying(20),
    document_number character varying(20) NOT NULL,
    birth_date date,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT chk_customers_email CHECK ((POSITION(('@'::text) IN (email)) > 1))
);


--
-- Name: TABLE customers; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.customers IS 'Marketplace customers';


--
-- Name: COLUMN customers.customer_id; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON COLUMN marketplace.customers.customer_id IS 'Customer unique identifier';


--
-- Name: COLUMN customers.document_number; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON COLUMN marketplace.customers.document_number IS 'CPF or equivalent identification';


--
-- Name: COLUMN customers.deleted_at; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON COLUMN marketplace.customers.deleted_at IS 'Soft delete timestamp';


--
-- Name: inventories; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.inventories (
    inventory_id uuid DEFAULT gen_random_uuid() NOT NULL,
    warehouse_id uuid NOT NULL,
    product_id uuid NOT NULL,
    available_quantity integer DEFAULT 0 NOT NULL,
    reserved_quantity integer DEFAULT 0 NOT NULL,
    minimum_quantity integer DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_inventory_available CHECK ((available_quantity >= 0)),
    CONSTRAINT chk_inventory_minimum CHECK ((minimum_quantity >= 0)),
    CONSTRAINT chk_inventory_reserved CHECK ((reserved_quantity >= 0))
);


--
-- Name: TABLE inventories; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.inventories IS 'Current inventory per warehouse';


--
-- Name: inventory_movements; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.inventory_movements (
    movement_id uuid DEFAULT gen_random_uuid() NOT NULL,
    inventory_id uuid NOT NULL,
    movement_type character varying(20) NOT NULL,
    quantity integer NOT NULL,
    reason character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    order_id uuid,
    CONSTRAINT chk_inventory_movement_type CHECK (((movement_type)::text = ANY ((ARRAY['INBOUND'::character varying, 'OUTBOUND'::character varying, 'RESERVATION'::character varying, 'RELEASE'::character varying, 'ADJUSTMENT'::character varying])::text[]))),
    CONSTRAINT chk_inventory_quantity CHECK ((quantity > 0))
);


--
-- Name: TABLE inventory_movements; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.inventory_movements IS 'Inventory movement history';


--
-- Name: order_items; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.order_items (
    order_item_id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    product_id uuid NOT NULL,
    quantity integer NOT NULL,
    unit_price numeric(19,4) NOT NULL,
    total_price numeric(19,4) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_order_items_quantity CHECK ((quantity > 0)),
    CONSTRAINT chk_order_items_total CHECK ((total_price >= (0)::numeric)),
    CONSTRAINT chk_order_items_unit_price CHECK ((unit_price >= (0)::numeric))
);


--
-- Name: TABLE order_items; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.order_items IS 'Products purchased in each order';


--
-- Name: order_status_history; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.order_status_history (
    history_id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    previous_status character varying(20),
    current_status character varying(20) NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE order_status_history; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.order_status_history IS 'Order status change history';


--
-- Name: orders; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.orders (
    order_id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_number character varying(30) NOT NULL,
    customer_id uuid NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    total_amount numeric(19,4) NOT NULL,
    shipping_amount numeric(19,4) DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_orders_shipping CHECK ((shipping_amount >= (0)::numeric)),
    CONSTRAINT chk_orders_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'PAID'::character varying, 'PROCESSING'::character varying, 'SHIPPED'::character varying, 'DELIVERED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT chk_orders_total CHECK ((total_amount >= (0)::numeric))
);


--
-- Name: TABLE orders; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.orders IS 'Marketplace orders';


--
-- Name: payment_methods; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.payment_methods (
    payment_method_id uuid DEFAULT gen_random_uuid() NOT NULL,
    code character varying(30) NOT NULL,
    name character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE payment_methods; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.payment_methods IS 'Available payment methods';


--
-- Name: payments; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.payments (
    payment_id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    payment_method_id uuid NOT NULL,
    transaction_code character varying(100) NOT NULL,
    amount numeric(19,4) NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    authorized_at timestamp with time zone,
    paid_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_payments_amount CHECK ((amount >= (0)::numeric)),
    CONSTRAINT chk_payments_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'AUTHORIZED'::character varying, 'PAID'::character varying, 'FAILED'::character varying, 'CANCELLED'::character varying, 'REFUNDED'::character varying])::text[])))
);


--
-- Name: TABLE payments; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.payments IS 'Order payments';


--
-- Name: products; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.products (
    product_id uuid DEFAULT gen_random_uuid() NOT NULL,
    seller_id uuid NOT NULL,
    category_id uuid NOT NULL,
    sku character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    brand character varying(100),
    price numeric(19,4) NOT NULL,
    weight numeric(10,3),
    height numeric(10,2),
    width numeric(10,2),
    length numeric(10,2),
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT chk_products_price CHECK ((price >= (0)::numeric)),
    CONSTRAINT chk_products_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying, 'OUT_OF_STOCK'::character varying])::text[])))
);


--
-- Name: TABLE products; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.products IS 'Marketplace products';


--
-- Name: refunds; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.refunds (
    refund_id uuid DEFAULT gen_random_uuid() NOT NULL,
    payment_id uuid NOT NULL,
    amount numeric(19,4) NOT NULL,
    reason character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_refunds_amount CHECK ((amount >= (0)::numeric))
);


--
-- Name: TABLE refunds; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.refunds IS 'Payment refunds';


--
-- Name: reviews; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.reviews (
    review_id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    product_id uuid NOT NULL,
    rating smallint NOT NULL,
    title character varying(200),
    comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_reviews_rating CHECK (((rating >= 1) AND (rating <= 5)))
);


--
-- Name: TABLE reviews; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.reviews IS 'Customer product reviews';


--
-- Name: sellers; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.sellers (
    seller_id uuid DEFAULT gen_random_uuid() NOT NULL,
    company_name character varying(255) NOT NULL,
    trade_name character varying(255),
    document_number character varying(20) NOT NULL,
    email character varying(255) NOT NULL,
    phone_number character varying(20),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT chk_sellers_email CHECK ((POSITION(('@'::text) IN (email)) > 1))
);


--
-- Name: TABLE sellers; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.sellers IS 'Marketplace sellers';


--
-- Name: shipments; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.shipments (
    shipment_id uuid DEFAULT gen_random_uuid() NOT NULL,
    order_id uuid NOT NULL,
    carrier_id uuid NOT NULL,
    tracking_code character varying(100) NOT NULL,
    status character varying(20) DEFAULT 'CREATED'::character varying NOT NULL,
    shipped_at timestamp with time zone,
    estimated_delivery_at timestamp with time zone,
    delivered_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_shipments_status CHECK (((status)::text = ANY ((ARRAY['CREATED'::character varying, 'SHIPPED'::character varying, 'IN_TRANSIT'::character varying, 'DELIVERED'::character varying, 'RETURNED'::character varying])::text[])))
);


--
-- Name: TABLE shipments; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.shipments IS 'Marketplace shipments';


--
-- Name: warehouses; Type: TABLE; Schema: marketplace; Owner: -
--

CREATE TABLE marketplace.warehouses (
    warehouse_id uuid DEFAULT gen_random_uuid() NOT NULL,
    code character varying(20) NOT NULL,
    name character varying(150) NOT NULL,
    street character varying(255),
    city character varying(100) NOT NULL,
    state character varying(100) NOT NULL,
    country character varying(100) DEFAULT 'Brazil'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);


--
-- Name: TABLE warehouses; Type: COMMENT; Schema: marketplace; Owner: -
--

COMMENT ON TABLE marketplace.warehouses IS 'Marketplace warehouses';


--
-- Name: carriers carriers_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.carriers
    ADD CONSTRAINT carriers_pkey PRIMARY KEY (carrier_id);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (category_id);


--
-- Name: customer_addresses customer_addresses_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.customer_addresses
    ADD CONSTRAINT customer_addresses_pkey PRIMARY KEY (address_id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (customer_id);


--
-- Name: inventories inventories_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.inventories
    ADD CONSTRAINT inventories_pkey PRIMARY KEY (inventory_id);


--
-- Name: inventory_movements inventory_movements_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.inventory_movements
    ADD CONSTRAINT inventory_movements_pkey PRIMARY KEY (movement_id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (order_item_id);


--
-- Name: order_status_history order_status_history_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.order_status_history
    ADD CONSTRAINT order_status_history_pkey PRIMARY KEY (history_id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (order_id);


--
-- Name: payment_methods payment_methods_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.payment_methods
    ADD CONSTRAINT payment_methods_pkey PRIMARY KEY (payment_method_id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (payment_id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (product_id);


--
-- Name: refunds refunds_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.refunds
    ADD CONSTRAINT refunds_pkey PRIMARY KEY (refund_id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (review_id);


--
-- Name: sellers sellers_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.sellers
    ADD CONSTRAINT sellers_pkey PRIMARY KEY (seller_id);


--
-- Name: shipments shipments_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.shipments
    ADD CONSTRAINT shipments_pkey PRIMARY KEY (shipment_id);


--
-- Name: carriers uq_carriers_code; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.carriers
    ADD CONSTRAINT uq_carriers_code UNIQUE (code);


--
-- Name: customers uq_customers_document_number; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.customers
    ADD CONSTRAINT uq_customers_document_number UNIQUE (document_number);


--
-- Name: customers uq_customers_email; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.customers
    ADD CONSTRAINT uq_customers_email UNIQUE (email);


--
-- Name: inventories uq_inventory_product; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.inventories
    ADD CONSTRAINT uq_inventory_product UNIQUE (warehouse_id, product_id);


--
-- Name: orders uq_orders_order_number; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.orders
    ADD CONSTRAINT uq_orders_order_number UNIQUE (order_number);


--
-- Name: payment_methods uq_payment_methods_code; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.payment_methods
    ADD CONSTRAINT uq_payment_methods_code UNIQUE (code);


--
-- Name: payments uq_payments_order; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.payments
    ADD CONSTRAINT uq_payments_order UNIQUE (order_id);


--
-- Name: payments uq_payments_transaction; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.payments
    ADD CONSTRAINT uq_payments_transaction UNIQUE (transaction_code);


--
-- Name: products uq_products_sku; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.products
    ADD CONSTRAINT uq_products_sku UNIQUE (sku);


--
-- Name: reviews uq_reviews_order_product; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.reviews
    ADD CONSTRAINT uq_reviews_order_product UNIQUE (order_id, product_id);


--
-- Name: sellers uq_sellers_document; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.sellers
    ADD CONSTRAINT uq_sellers_document UNIQUE (document_number);


--
-- Name: sellers uq_sellers_email; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.sellers
    ADD CONSTRAINT uq_sellers_email UNIQUE (email);


--
-- Name: shipments uq_shipments_tracking_code; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.shipments
    ADD CONSTRAINT uq_shipments_tracking_code UNIQUE (tracking_code);


--
-- Name: warehouses uq_warehouses_code; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.warehouses
    ADD CONSTRAINT uq_warehouses_code UNIQUE (code);


--
-- Name: warehouses warehouses_pkey; Type: CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.warehouses
    ADD CONSTRAINT warehouses_pkey PRIMARY KEY (warehouse_id);


--
-- Name: idx_categories_parent_category_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_categories_parent_category_id ON marketplace.categories USING btree (parent_category_id);


--
-- Name: idx_customer_addresses_customer_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_customer_addresses_customer_id ON marketplace.customer_addresses USING btree (customer_id);


--
-- Name: idx_customers_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_customers_created_at ON marketplace.customers USING btree (created_at);


--
-- Name: idx_customers_updated_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_customers_updated_at ON marketplace.customers USING btree (updated_at);


--
-- Name: idx_inventories_product_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_inventories_product_id ON marketplace.inventories USING btree (product_id);


--
-- Name: idx_inventories_warehouse_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_inventories_warehouse_id ON marketplace.inventories USING btree (warehouse_id);


--
-- Name: idx_inventory_movements_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_inventory_movements_created_at ON marketplace.inventory_movements USING btree (created_at);


--
-- Name: idx_inventory_movements_inventory_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_inventory_movements_inventory_id ON marketplace.inventory_movements USING btree (inventory_id);


--
-- Name: idx_inventory_movements_order_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_inventory_movements_order_id ON marketplace.inventory_movements USING btree (order_id);


--
-- Name: idx_inventory_movements_type; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_inventory_movements_type ON marketplace.inventory_movements USING btree (movement_type);


--
-- Name: idx_order_items_order_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_order_items_order_id ON marketplace.order_items USING btree (order_id);


--
-- Name: idx_order_items_product_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_order_items_product_id ON marketplace.order_items USING btree (product_id);


--
-- Name: idx_order_status_history_changed_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_order_status_history_changed_at ON marketplace.order_status_history USING btree (changed_at);


--
-- Name: idx_order_status_history_order_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_order_status_history_order_id ON marketplace.order_status_history USING btree (order_id);


--
-- Name: idx_orders_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_orders_created_at ON marketplace.orders USING btree (created_at);


--
-- Name: idx_orders_customer_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_orders_customer_id ON marketplace.orders USING btree (customer_id);


--
-- Name: idx_orders_status; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_orders_status ON marketplace.orders USING btree (status);


--
-- Name: idx_orders_updated_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_orders_updated_at ON marketplace.orders USING btree (updated_at);


--
-- Name: idx_payments_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_payments_created_at ON marketplace.payments USING btree (created_at);


--
-- Name: idx_payments_order_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_payments_order_id ON marketplace.payments USING btree (order_id);


--
-- Name: idx_payments_paid_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_payments_paid_at ON marketplace.payments USING btree (paid_at);


--
-- Name: idx_payments_payment_method_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_payments_payment_method_id ON marketplace.payments USING btree (payment_method_id);


--
-- Name: idx_payments_status; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_payments_status ON marketplace.payments USING btree (status);


--
-- Name: idx_products_category_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_products_category_id ON marketplace.products USING btree (category_id);


--
-- Name: idx_products_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_products_created_at ON marketplace.products USING btree (created_at);


--
-- Name: idx_products_seller_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_products_seller_id ON marketplace.products USING btree (seller_id);


--
-- Name: idx_products_status; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_products_status ON marketplace.products USING btree (status);


--
-- Name: idx_refunds_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_refunds_created_at ON marketplace.refunds USING btree (created_at);


--
-- Name: idx_refunds_payment_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_refunds_payment_id ON marketplace.refunds USING btree (payment_id);


--
-- Name: idx_reviews_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_reviews_created_at ON marketplace.reviews USING btree (created_at);


--
-- Name: idx_reviews_customer_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_reviews_customer_id ON marketplace.reviews USING btree (customer_id);


--
-- Name: idx_reviews_product_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_reviews_product_id ON marketplace.reviews USING btree (product_id);


--
-- Name: idx_sellers_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_sellers_created_at ON marketplace.sellers USING btree (created_at);


--
-- Name: idx_sellers_updated_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_sellers_updated_at ON marketplace.sellers USING btree (updated_at);


--
-- Name: idx_shipments_carrier_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_shipments_carrier_id ON marketplace.shipments USING btree (carrier_id);


--
-- Name: idx_shipments_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_shipments_created_at ON marketplace.shipments USING btree (created_at);


--
-- Name: idx_shipments_delivered_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_shipments_delivered_at ON marketplace.shipments USING btree (delivered_at);


--
-- Name: idx_shipments_order_id; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_shipments_order_id ON marketplace.shipments USING btree (order_id);


--
-- Name: idx_shipments_status; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_shipments_status ON marketplace.shipments USING btree (status);


--
-- Name: idx_warehouses_created_at; Type: INDEX; Schema: marketplace; Owner: -
--

CREATE INDEX idx_warehouses_created_at ON marketplace.warehouses USING btree (created_at);


--
-- Name: categories fk_categories_parent; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.categories
    ADD CONSTRAINT fk_categories_parent FOREIGN KEY (parent_category_id) REFERENCES marketplace.categories(category_id);


--
-- Name: customer_addresses fk_customer_addresses_customer; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.customer_addresses
    ADD CONSTRAINT fk_customer_addresses_customer FOREIGN KEY (customer_id) REFERENCES marketplace.customers(customer_id) ON DELETE CASCADE;


--
-- Name: inventories fk_inventories_product; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.inventories
    ADD CONSTRAINT fk_inventories_product FOREIGN KEY (product_id) REFERENCES marketplace.products(product_id) ON DELETE RESTRICT;


--
-- Name: inventories fk_inventories_warehouse; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.inventories
    ADD CONSTRAINT fk_inventories_warehouse FOREIGN KEY (warehouse_id) REFERENCES marketplace.warehouses(warehouse_id) ON DELETE RESTRICT;


--
-- Name: inventory_movements fk_inventory_movements_inventory; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.inventory_movements
    ADD CONSTRAINT fk_inventory_movements_inventory FOREIGN KEY (inventory_id) REFERENCES marketplace.inventories(inventory_id) ON DELETE RESTRICT;


--
-- Name: inventory_movements fk_inventory_movements_order; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.inventory_movements
    ADD CONSTRAINT fk_inventory_movements_order FOREIGN KEY (order_id) REFERENCES marketplace.orders(order_id) ON DELETE SET NULL;


--
-- Name: order_items fk_order_items_order; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.order_items
    ADD CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES marketplace.orders(order_id) ON DELETE CASCADE;


--
-- Name: order_items fk_order_items_product; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.order_items
    ADD CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES marketplace.products(product_id) ON DELETE RESTRICT;


--
-- Name: order_status_history fk_order_status_history_order; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.order_status_history
    ADD CONSTRAINT fk_order_status_history_order FOREIGN KEY (order_id) REFERENCES marketplace.orders(order_id) ON DELETE CASCADE;


--
-- Name: orders fk_orders_customer; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.orders
    ADD CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES marketplace.customers(customer_id) ON DELETE RESTRICT;


--
-- Name: payments fk_payments_order; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.payments
    ADD CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES marketplace.orders(order_id) ON DELETE RESTRICT;


--
-- Name: payments fk_payments_payment_method; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.payments
    ADD CONSTRAINT fk_payments_payment_method FOREIGN KEY (payment_method_id) REFERENCES marketplace.payment_methods(payment_method_id) ON DELETE RESTRICT;


--
-- Name: products fk_products_category; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.products
    ADD CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES marketplace.categories(category_id) ON DELETE RESTRICT;


--
-- Name: products fk_products_seller; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.products
    ADD CONSTRAINT fk_products_seller FOREIGN KEY (seller_id) REFERENCES marketplace.sellers(seller_id) ON DELETE RESTRICT;


--
-- Name: refunds fk_refunds_payment; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.refunds
    ADD CONSTRAINT fk_refunds_payment FOREIGN KEY (payment_id) REFERENCES marketplace.payments(payment_id) ON DELETE RESTRICT;


--
-- Name: reviews fk_reviews_customer; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.reviews
    ADD CONSTRAINT fk_reviews_customer FOREIGN KEY (customer_id) REFERENCES marketplace.customers(customer_id) ON DELETE RESTRICT;


--
-- Name: reviews fk_reviews_order; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.reviews
    ADD CONSTRAINT fk_reviews_order FOREIGN KEY (order_id) REFERENCES marketplace.orders(order_id) ON DELETE RESTRICT;


--
-- Name: reviews fk_reviews_product; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.reviews
    ADD CONSTRAINT fk_reviews_product FOREIGN KEY (product_id) REFERENCES marketplace.products(product_id) ON DELETE RESTRICT;


--
-- Name: shipments fk_shipments_carrier; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.shipments
    ADD CONSTRAINT fk_shipments_carrier FOREIGN KEY (carrier_id) REFERENCES marketplace.carriers(carrier_id) ON DELETE RESTRICT;


--
-- Name: shipments fk_shipments_order; Type: FK CONSTRAINT; Schema: marketplace; Owner: -
--

ALTER TABLE ONLY marketplace.shipments
    ADD CONSTRAINT fk_shipments_order FOREIGN KEY (order_id) REFERENCES marketplace.orders(order_id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--


"""


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP SCHEMA marketplace CASCADE")
