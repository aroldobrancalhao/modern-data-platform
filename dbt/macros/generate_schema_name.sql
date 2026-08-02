{#
    dbt-core's default (dbt/include/global_project/macros/get_custom_name/
    get_custom_schema.sql) concatenates the profile's default schema with
    any custom schema: {{ target.schema }}_{{ custom_schema_name }} --
    e.g. mdp_silver_dev_mdp_gold_dev instead of mdp_gold_dev. dbt-athena
    doesn't override this macro, so it inherits the default behavior.

    Standard documented override: use the custom schema alone when one
    is set, ignoring the profile's default schema entirely.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}

        {{ default_schema }}

    {%- else -%}

        {{ custom_schema_name | trim }}

    {%- endif -%}

{%- endmacro %}
