##########################################################
# CloudWatch
##########################################################

module "cloudwatch_airflow" {
  source = "../../modules/monitoring/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/airflow"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_glue" {
  source = "../../modules/monitoring/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/glue"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_databricks" {
  source = "../../modules/monitoring/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/databricks"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_athena" {
  source = "../../modules/monitoring/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/athena"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_platform" {
  source = "../../modules/monitoring/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/platform"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_terraform" {
  source = "../../modules/monitoring/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/terraform"
  retention_in_days = 30

  tags = local.default_tags
}