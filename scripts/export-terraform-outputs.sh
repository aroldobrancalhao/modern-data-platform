#!/usr/bin/env bash

set -e

# Resolves paths relative to the repo root regardless of the caller's
# CWD -- SCRIPT_DIR is this file's own directory (scripts/), REPO_ROOT
# one level up. The script previously used a bare relative path
# (`airflow/config/terraform_outputs.json`) that only ever resolved
# correctly if invoked from the repo root, while `terraform output`
# needs to run against the environments/dev working dir -- two
# incompatible CWD requirements in one un-`cd`'d script. Fixed here
# rather than left broken while this file was already being touched.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TF_DIR="$REPO_ROOT/infrastructure/terraform/environments/dev"

terraform -chdir="$TF_DIR" output -json > "$REPO_ROOT/airflow/config/terraform_outputs.json"

# AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN (infrastructure/docker/.env) can't
# be picked up from terraform_outputs.json above the way aws_region
# and the other outputs are -- that file is consumed by Python
# bootstrap code (airflow/config/bootstrap/terraform.py) *inside* the
# Airflow containers at runtime, but this specific value is needed by
# docker-compose.yml's own `${...}` substitution *before* any
# container starts (it feeds AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER
# directly) -- a different consumption point the JSON pipeline never
# reaches. Synced into .env here instead, so it's derived from
# Terraform state instead of hand-typed -- see
# docs/architecture/roadmap-next-steps.md.
ENV_FILE="$REPO_ROOT/infrastructure/docker/.env"
ARN="$(terraform -chdir="$TF_DIR" output -raw airflow_cloudwatch_log_group_arn)"

if [ -f "$ENV_FILE" ]; then
  if grep -q "^AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN=" "$ENV_FILE"; then
    sed -i "s#^AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN=.*#AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN=${ARN}#" "$ENV_FILE"
  else
    echo "AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN=${ARN}" >> "$ENV_FILE"
  fi
fi
