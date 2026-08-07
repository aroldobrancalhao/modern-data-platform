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
--
-- external_location is explicit: the workgroup (mdp-athena-dev) has
-- enforce_workgroup_configuration=true with a fixed output location,
-- which makes dbt-athena ignore s3_data_dir/s3_data_naming
-- (schema_table) for CTAS tables -- confirmed in the adapter's
-- generate_s3_location() source: it never checks workgroup
-- enforcement when external_location is set, only when falling back
-- to s3_data_dir/s3_staging_dir. Path below mirrors the schema_table
-- naming already declared in profiles.yml (s3_data_dir/{schema}/
-- {table}/), made explicit since the implicit computation is a no-op
-- under this workgroup config.

{{ config(
    materialized='table',
    external_location='s3://mdp-datalake-dev-857854758128/gold/mdp_gold_dev/dim_customers/'
) }}

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
