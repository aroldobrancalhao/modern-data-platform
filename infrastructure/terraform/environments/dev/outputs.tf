output "environment" {
  value = "dev"
}

output "aws_region" {
  value = var.aws_region
}

output "datalake_bucket" {
  value = module.datalake.bucket_name
}

output "airflow_cloudwatch_log_group_arn" {
  description = "ARN of Airflow's CloudWatch log group (module.cloudwatch_airflow, monitoring.tf). Not sensitive (a resource identifier, not a credential) -- unlike the access-key outputs below, safe to print directly. Feeds infrastructure/docker/.env's AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN (consumed by docker-compose.yml's AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER) via scripts/export-terraform-outputs.sh, instead of being hand-typed -- see roadmap-next-steps.md."
  value       = module.cloudwatch_airflow.arn
}

output "platform_cloudwatch_log_group_name" {
  description = "Name (not ARN -- watchtower's CloudWatchLogHandler takes log_group_name, not an ARN) of the platform CloudWatch log group (module.cloudwatch_platform, monitoring.tf). Not sensitive. Feeds infrastructure/docker/.env's PLATFORM_CLOUDWATCH_LOG_GROUP via scripts/export-terraform-outputs.sh, same pattern as airflow_cloudwatch_log_group_arn above -- see roadmap-next-steps.md, Sprint 13 close-out."
  value       = module.cloudwatch_platform.name
}

output "databricks_cloudwatch_log_group_name" {
  description = "Name (not ARN) of the databricks CloudWatch log group (module.cloudwatch_databricks, monitoring.tf). Not sensitive. Feeds infrastructure/docker/.env's DATABRICKS_CLOUDWATCH_LOG_GROUP via scripts/export-terraform-outputs.sh, same pattern as platform_cloudwatch_log_group_name above -- see roadmap-next-steps.md, Sprint 13 close-out."
  value       = module.cloudwatch_databricks.name
}

output "bronze_database" {
  value = module.glue_bronze.database_name
}

output "silver_database" {
  value = module.glue_silver.database_name
}

output "gold_database" {
  value = module.glue_gold.database_name
}

output "athena_workgroup" {
  value = module.athena.workgroup_name
}

output "databricks_uc_role_arn" {
  value = aws_iam_role.databricks_uc.arn
}

output "bi_reader_access_key_id" {
  description = "Access Key ID for the BI Reader IAM User (Metabase/Power BI). Not a secret on its own, but paired here with the secret key -- treat the pair as sensitive."
  value       = module.bi_reader.access_key_id
  sensitive   = true
}

output "bi_reader_secret_access_key" {
  description = "Secret Access Key for the BI Reader IAM User (Metabase/Power BI). Read once with `terraform output -raw bi_reader_secret_access_key` and paste into infrastructure/docker/.env -- never logged or committed."
  value       = module.bi_reader.secret_access_key
  sensitive   = true
}

output "airflow_ingest_access_key_id" {
  description = "Access Key ID for the Airflow Ingest IAM User (extract_postgres + CloudWatch remote logging). Not a secret on its own, but paired here with the secret key -- treat the pair as sensitive."
  value       = module.airflow_ingest.access_key_id
  sensitive   = true
}

output "airflow_ingest_secret_access_key" {
  description = "Secret Access Key for the Airflow Ingest IAM User. Read once with `terraform output -raw airflow_ingest_secret_access_key` and paste into infrastructure/docker/.env -- never logged or committed."
  value       = module.airflow_ingest.secret_access_key
  sensitive   = true
}

output "bronze_consumer_access_key_id" {
  description = "Access Key ID for the Bronze Consumer IAM User (bronze/ S3 read-write only). Not a secret on its own, but paired here with the secret key -- treat the pair as sensitive. Not wired into infrastructure/docker/docker-compose.yml yet -- bronze-consumer still runs on MDP_PERSONAL_ACCESS_KEY_ID/SECRET, see roadmap-next-steps.md."
  value       = module.bronze_consumer.access_key_id
  sensitive   = true
}

output "bronze_consumer_secret_access_key" {
  description = "Secret Access Key for the Bronze Consumer IAM User. Read once with `terraform output -raw bronze_consumer_secret_access_key` and paste into infrastructure/docker/.env when the credential swap itself is approved -- never logged or committed."
  value       = module.bronze_consumer.secret_access_key
  sensitive   = true
}

output "dbt_gold_access_key_id" {
  description = "Access Key ID for the dbt (Gold build) IAM User (mdp-athena-dbt-dev, Glue read mdp_silver_dev / write mdp_gold_dev, S3 read silver/ + read-write gold/). Not a secret on its own, but paired here with the secret key -- treat the pair as sensitive. Not wired into airflow/dags/marketplace_batch_pipeline.py yet -- dbt_run_gold/dbt_test_gold still override onto MDP_PERSONAL_ACCESS_KEY_ID/SECRET, see roadmap-next-steps.md."
  value       = module.dbt_gold.access_key_id
  sensitive   = true
}

output "dbt_gold_secret_access_key" {
  description = "Secret Access Key for the dbt (Gold build) IAM User. Read once with `terraform output -raw dbt_gold_secret_access_key` and paste into infrastructure/docker/.env when that credential swap is approved -- never logged or committed."
  value       = module.dbt_gold.secret_access_key
  sensitive   = true
}
