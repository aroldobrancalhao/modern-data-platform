#!/usr/bin/env bash

set -e

terraform output -json > airflow/config/terraform_outputs.json