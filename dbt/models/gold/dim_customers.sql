-- Grain: one row per customer (same as stg_customers). Natural key
-- (customer_id) used directly -- no precedent for surrogate keys
-- anywhere in this repo, and a single-source, single-grain dimension
-- like this one has no join-collision reason to need one. Plain
-- latest-state dimension, not SCD2: no snapshot exists yet for
-- customers (dbt/snapshots/ is empty), and ADR-005's "snapshots
-- should be used for historical tracking" is a general principle, not
-- evidence a customer-history requirement exists today. Revisit if/
-- when a real point-in-time customer attribute need shows up.
--
-- materialized='table': final-layer dim/fact benefit from physical
-- materialization, unlike stg_/int_ which stay view by staging
-- convention.

{{ config(materialized='table') }}

select
    customer_id,
    first_name,
    last_name,
    email,
    phone_number,
    document_number,
    birth_date,
    is_active,
    created_at,
    updated_at,
    deleted_at

from {{ ref('stg_customers') }}
