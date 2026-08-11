terraform {
  # Intentionally empty -- partial backend configuration.
  #
  # Terraform's backend {} block can't reference var.*/local.* (a
  # hard language restriction, not a choice -- confirmed while
  # investigating the "mdp-" hardcoded-name portability pass, see
  # docs/architecture/roadmap-next-steps.md), so bucket/key/region
  # can't be interpolated from var.project_name/var.account_id the
  # way every other resource in this repo now is. The idiomatic
  # Terraform answer to that specific restriction is partial backend
  # configuration: this block declares only the backend *type* (s3),
  # and the real values live in backend-dev.hcl. Tracked in git, not
  # gitignored -- the bucket name (which embeds the AWS account id)
  # was already public in this repo's history via the hardcoded
  # backend.tf this file replaces, so moving the same value to its
  # own file changes nothing about that, and gitignoring it would
  # break `git clone` + the documented init flow for everyone.
  # Passed explicitly via
  #
  #   terraform init -backend-config=backend-dev.hcl
  #
  # instead of a bare `terraform init`. See the README's Terraform
  # section for the full init flow -- this is a deliberate change to
  # the init command, not a regression.
  backend "s3" {}
}
