# Modern Data Platform
#
# Sprint 14, item 2. Named exactly `terraform.tfvars` -- one of the
# filenames Terraform auto-loads on every plan/apply with no flag
# needed (the other being `*.auto.tfvars`), eliminating the 6 -var
# flags every real command this session had to type by hand.
#
# Tracked in git, not gitignored -- evaluated deliberately, not
# assumed safe: none of these are credentials. account_id
# (857854758128) looks like it could be sensitive, but isn't a new
# exposure here -- it's already public in this repo's own git history,
# baked into every real resource name this project has ever created
# (mdp-tfstate-857854758128, mdp-datalake-dev-857854758128, ...) since
# before this file existed. A real secret (an access key, a token) would
# belong in a separate, gitignored -var-file or an environment variable
# instead -- this project already follows that split for actual
# credentials (see infrastructure/docker/.env, TELEGRAM_BOT_TOKEN, the
# various *_SECRET_ACCESS_KEY entries) via a completely different
# mechanism (Terraform outputs read once and pasted in, never a .tfvars
# value in the first place).

aws_region   = "sa-east-1"
project_name = "mdp"
environment  = "dev"
account_id   = "857854758128"
owner        = "Aroldo Brancalhão"
repository   = "modern-data-platform"

# databricks_uc_external_id deliberately NOT set here -- it already has
# a real, safe default in variables.tf (the actual external ID
# Databricks returned for the real storage credential), and duplicating
# it here would just be a second copy that could silently drift from
# that source of truth.
