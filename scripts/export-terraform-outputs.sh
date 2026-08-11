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

# AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN and (added Sprint 13 close-out)
# PLATFORM_CLOUDWATCH_LOG_GROUP (infrastructure/docker/.env) can't be
# picked up from terraform_outputs.json above the way aws_region and
# the other outputs are -- that file is consumed by Python bootstrap
# code (airflow/config/bootstrap/terraform.py) *inside* the Airflow
# containers at runtime, but these two values are needed by
# docker-compose.yml's own `${...}` substitution *before* any
# container starts (they feed AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER
# and the bronze-consumer/Airflow LOG_CLOUDWATCH_LOG_GROUP env vars
# directly) -- a different consumption point the JSON pipeline never
# reaches. Synced into .env here instead, so both are derived from
# Terraform state instead of hand-typed -- see
# docs/architecture/roadmap-next-steps.md.
ENV_FILE="$REPO_ROOT/infrastructure/docker/.env"

sync_env_var() {
  local var_name="$1"
  local value="$2"

  if [ -f "$ENV_FILE" ]; then
    if grep -q "^${var_name}=" "$ENV_FILE"; then
      sed -i "s#^${var_name}=.*#${var_name}=${value}#" "$ENV_FILE"
    else
      echo "${var_name}=${value}" >> "$ENV_FILE"
    fi
  fi
}

sync_env_var "AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN" \
  "$(terraform -chdir="$TF_DIR" output -raw airflow_cloudwatch_log_group_arn)"

sync_env_var "PLATFORM_CLOUDWATCH_LOG_GROUP" \
  "$(terraform -chdir="$TF_DIR" output -raw platform_cloudwatch_log_group_name)"

sync_env_var "DATABRICKS_CLOUDWATCH_LOG_GROUP" \
  "$(terraform -chdir="$TF_DIR" output -raw databricks_cloudwatch_log_group_name)"
