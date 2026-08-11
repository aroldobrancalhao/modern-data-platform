##########################################################
# CloudWatch
##########################################################
#
# glue and athena log groups deliberately removed (Sprint 13
# close-out, 2026-08-11) -- confirmed against AWS docs, not assumed:
# Glue's CloudWatch logging is opt-in per job
# (--enable-continuous-cloudwatch-log) and this project has zero Glue
# Jobs/Crawlers to attach it to (only Glue Data Catalog databases via
# module.catalog); Athena has no CloudWatch Logs mechanism at all for
# query execution, only CloudWatch metrics and CloudTrail API audit
# (docs.aws.amazon.com/athena/latest/ug/security-logging-monitoring.html).
# Both log groups had zero possible producer, ever -- dead
# infrastructure by design, same disposal criteria as ADR-013. See
# roadmap-next-steps.md for the full Sprint 13 close-out record.

module "cloudwatch_airflow" {
  source = "../../modules/monitoring/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/airflow"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_databricks" {
  source = "../../modules/monitoring/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/databricks"
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