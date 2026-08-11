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

# 21 instances below -- one per resource that had its real AWS name
# hardcoded as a literal "mdp-..."/"mdp_..." string (analytics.tf,
# catalog.tf, security.tf), same pattern as the 2 bucket instances
# above. account_id is unused by every one of these (only
# .resource_prefix/.resource_prefix_underscore are referenced, never
# .bucket_name) but is still required by the module's own variables.tf
# -- passed through for consistency, not because any of these need it.
# See docs/architecture/roadmap-next-steps.md for the full portability
# writeup, including why this is a genuinely zero-impact refactor
# (var.project_name="mdp"/var.environment="dev" are the only values
# ever used, so every interpolated result below is byte-identical to
# today's literal -- confirmed via `terraform plan`, not assumed).

module "naming_athena" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "athena"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_athena_dbt_build" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "athena-dbt"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_glue_bronze" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "bronze"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_glue_bronze_crawler" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "bronze-crawler"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_glue_silver" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "silver"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_glue_silver_crawler" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "silver-crawler"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_glue_gold" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "gold"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_glue_gold_crawler" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "gold-crawler"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_databricks_role" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "databricks-role"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_datalake_policy" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "datalake-policy"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_databricks_uc_role" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "databricks-uc-role"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_glue_role" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "glue-role"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_glue_policy" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "glue-policy"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_bi_reader" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "bi-reader"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_bi_reader_policy" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "bi-reader-policy"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_airflow_ingest" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "airflow-ingest"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_airflow_ingest_policy" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "airflow-ingest-policy"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_bronze_consumer" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "bronze-consumer"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_bronze_consumer_policy" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "bronze-consumer-policy"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_dbt_gold" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "dbt-gold"
  environment   = var.environment
  account_id    = var.account_id
}

module "naming_dbt_gold_policy" {
  source = "../../modules/foundation/naming"

  project_name  = var.project_name
  resource_name = "dbt-gold-policy"
  environment   = var.environment
  account_id    = var.account_id
}