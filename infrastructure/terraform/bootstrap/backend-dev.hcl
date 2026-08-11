# Modern Data Platform
#
# Backend config for infrastructure/terraform/bootstrap -- pairs with
# backend.tf's empty `backend "s3" {}` block (partial backend
# configuration). Same real values the block used to hardcode
# directly; see backend.tf's own comment for why this got split out.
#
# Usage:
#   terraform init -backend-config=backend-dev.hcl

bucket = "mdp-tfstate-857854758128"
key    = "bootstrap/terraform.tfstate"
region = "sa-east-1"

# State locking, Sprint 14 -- same reasoning as
# environments/dev/backend-dev.hcl's own comment: native S3 locking
# (use_lockfile), not DynamoDB (deprecated as of the installed
# Terraform version, 1.15.8). Zero new AWS resources.
use_lockfile = true
