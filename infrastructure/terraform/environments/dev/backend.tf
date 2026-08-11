terraform {
  # Intentionally empty -- partial backend configuration. See
  # bootstrap/backend.tf's own comment for the full reasoning (backend
  # {} blocks can't reference var.*/local.*, a hard Terraform
  # restriction -- confirmed while investigating the "mdp-" hardcoded-
  # name portability pass, docs/architecture/roadmap-next-steps.md).
  # Real values live in backend-dev.hcl (tracked in git, same file
  # this replaces just relocated -- no new sensitivity), passed via
  #
  #   terraform init -backend-config=backend-dev.hcl
  #
  # instead of a bare `terraform init`.
  backend "s3" {}
}
