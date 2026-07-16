output "datalake_bucket_name" {
  value = module.datalake.bucket_name
}

output "datalake_bucket_arn" {
  value = module.datalake.bucket_arn
}

output "athena_workgroup_name" {
  description = "Athena Workgroup name."

  value = module.athena.workgroup_name
}

output "athena_workgroup_arn" {
  description = "Athena Workgroup ARN."

  value = module.athena.workgroup_arn
}