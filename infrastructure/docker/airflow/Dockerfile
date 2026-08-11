FROM apache/airflow:3.3.0

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Airflow provider packages (operators/hooks the DAGs use directly --
# not part of the app's own pyproject.toml, which only tracks the
# app's own runtime dependencies). statsd is here rather than below
# for the same reason: it's required for
# AIRFLOW__METRICS__STATSD_ON (see docker-compose.yml), not imported
# by any src/ code.
RUN pip install --no-cache-dir \
    apache-airflow-providers-amazon \
    apache-airflow-providers-postgres \
    apache-airflow-providers-http \
    apache-airflow-providers-databricks \
    "statsd>=4.0.1"

# The full [project.dependencies] set from pyproject.toml, same
# version floors -- every DAG that imports the project's own src/
# code (data_platform/integrations) needs all of it importable, not
# just whatever a given task happens to touch first. apache-airflow
# and apache-airflow-providers-standard are excluded: the former is
# this image itself, the latter already ships in the base image.
# polars/duckdb aren't in pyproject.toml (not imported by src/ today)
# but were already part of this project's pre-existing dependency
# list before this Dockerfile existed -- kept for parity.
RUN pip install --no-cache-dir \
    "alembic>=1.18.5" \
    "boto3>=1.43.52" \
    "confluent-kafka>=2.15.0" \
    "databricks-sdk>=0.122.0" \
    "dbt-athena>=1.11.0" \
    "dbt-core>=1.12.0" \
    "deltalake>=1.6.2" \
    "faker>=40.28.1" \
    "httpx>=0.28.1" \
    "jinja2>=3.1.6" \
    "prometheus-client>=0.21.0" \
    "psycopg2-binary>=2.9.12" \
    "psycopg[binary]>=3.3.4" \
    "pyarrow>=25.0.0" \
    "pydantic>=2.13.4" \
    "pydantic-settings>=2.14.2" \
    "python-dotenv>=1.2.2" \
    "pyyaml>=6.0.3" \
    "structlog>=26.1.0" \
    "watchtower>=3.4.0" \
    polars \
    duckdb
