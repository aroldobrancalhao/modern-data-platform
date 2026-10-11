FROM apache/airflow:3.3.0

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Exact versions of every installed package, transitive ones included
# (see the file's header). Applied to both pip installs below.
COPY airflow/constraints.txt /tmp/mdp-constraints.txt

# Airflow provider packages (operators/hooks the DAGs use directly --
# not part of the app's own pyproject.toml, which only tracks the
# app's own runtime dependencies). statsd is here rather than below
# for the same reason: it's required for
# AIRFLOW__METRICS__STATSD_ON (see docker-compose.yml), not imported
# by any src/ code.
RUN pip install --no-cache-dir -c /tmp/mdp-constraints.txt \
    apache-airflow-providers-amazon==9.31.0 \
    apache-airflow-providers-postgres==6.8.0 \
    apache-airflow-providers-http==6.0.4 \
    apache-airflow-providers-databricks==7.18.0 \
    "statsd==4.0.1"

# The full [project.dependencies] set from pyproject.toml -- every DAG that imports the project's own src/
# code (data_platform/integrations) needs all of it importable, not
# just whatever a given task happens to touch first. apache-airflow
# and apache-airflow-providers-standard are excluded: the former is
# this image itself, the latter already ships in the base image.
# polars/duckdb aren't in pyproject.toml (not imported by src/ today)
# but were already part of this project's pre-existing dependency
# list before this Dockerfile existed -- kept for parity.
# Every package in this file is pinned (==) to the version the running
# images had on 2026-10-11, so a rebuild reproduces them instead of
# silently resolving newer releases.
RUN pip install --no-cache-dir -c /tmp/mdp-constraints.txt \
    "alembic==1.18.5" \
    "boto3==1.43.64" \
    "confluent-kafka==2.15.0" \
    "databricks-sdk==0.123.0" \
    "dbt-athena==1.11.0" \
    "dbt-core==1.12.0" \
    "deltalake==1.6.2" \
    "faker==40.36.0" \
    "httpx==0.28.1" \
    "jinja2==3.1.6" \
    "prometheus-client==0.25.0" \
    "psycopg2-binary==2.9.12" \
    "psycopg[binary]==3.3.4" \
    "pyarrow==25.0.0" \
    "pydantic==2.13.4" \
    "pydantic-settings==2.14.2" \
    "python-dotenv==1.2.2" \
    "pyyaml==6.0.3" \
    "structlog==26.1.0" \
    "watchtower==3.4.0" \
    polars==1.43.2 \
    duckdb==1.5.5
