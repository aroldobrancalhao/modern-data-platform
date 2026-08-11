# Modern Data Platform
#
# Backend config for infrastructure/terraform/environments/dev --
# pairs with backend.tf's empty `backend "s3" {}` block (partial
# backend configuration). Same real values the block used to hardcode
# directly; see backend.tf's own comment for why this got split out.
#
# Usage:
#   terraform init -backend-config=backend-dev.hcl

bucket = "mdp-tfstate-857854758128"
key    = "environments/dev/terraform.tfstate"
region = "sa-east-1"

# State locking, Sprint 14. Deliberately NOT a DynamoDB table --
# confirmed against the real installed Terraform version (1.15.8) and
# the official S3 backend docs before building anything: native S3
# locking (use_lockfile, generally available since 1.11, via S3
# conditional writes creating a real .tflock object next to the state
# file) is the current, recommended mechanism. DynamoDB-based locking
# is officially deprecated as of this version and slated for removal
# -- building a new DynamoDB module now would mean standing up
# infrastructure for an already-deprecated pattern. Zero new AWS
# resources needed for this.
use_lockfile = true
