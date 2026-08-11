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
