# Modern Data Platform
#
# Sprint 14, item 2. Same reasoning as
# environments/dev/terraform.tfvars's own comment -- auto-loaded by
# Terraform with no flag needed, tracked in git deliberately (none of
# these are credentials; terraform_state_bucket's account id is
# already public in this repo's history, same as environments/dev's
# account_id).

aws_region             = "sa-east-1"
project_name           = "mdp"
environment            = "dev"
owner                  = "Aroldo Brancalhão"
repository             = "modern-data-platform"
terraform_state_bucket = "mdp-tfstate-857854758128"
