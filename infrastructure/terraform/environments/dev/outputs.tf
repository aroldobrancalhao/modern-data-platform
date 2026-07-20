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