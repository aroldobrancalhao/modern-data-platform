output "environment" {
  value = "dev"
}

output "aws_region" {
  value = var.aws_region
}

output "datalake_bucket" {
  value = module.datalake.bucket_name
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