##########################################################
# Naming
##########################################################

module "naming" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "datalake"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_athena_staging" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "athena-staging"
  environment   = var.environment
  account_id    = var.account_id
}