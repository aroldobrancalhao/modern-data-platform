# Modern Data Platform
#
# Bronze Consumer image. Unlike airflow/Dockerfile, this is a plain
# Python runtime with nothing to reconcile against a base image's own
# providers/constraints -- dependencies are installed straight from
# this project's own lockfile, not mirrored by hand.

FROM python:3.12-slim

# uv itself, copied from its official distroless image -- pinned to
# the same version this project's uv.lock was produced with.
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /usr/local/bin/

WORKDIR /app

# Dependencies only. --no-install-project: this project has no
# [build-system] -- src/ is not an installable package (see
# docs/architecture/roadmap-next-steps.md, "src/ packages aren't
# installable -- PYTHONPATH required outside pytest"), only its
# [project.dependencies] are meant to be installed here.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Code added after the dependency layer so an app-only change doesn't
# invalidate the much slower `uv sync` layer above.
COPY src/ ./src/
COPY scripts/run_bronze_consumer.py ./scripts/run_bronze_consumer.py

ENV PYTHONPATH=/app/src

# /metrics, scraped by Prometheus (job "bronze-consumer" -- see
# monitoring/prometheus/prometheus.yml).
EXPOSE 9200

CMD ["/app/.venv/bin/python", "scripts/run_bronze_consumer.py"]
