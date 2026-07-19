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