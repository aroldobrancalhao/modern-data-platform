variable "workgroup_name" {
  description = "Athena Workgroup name."
  type        = string
}

variable "results_bucket" {
  description = "S3 bucket for Athena query results."
  type        = string
}

variable "results_prefix" {
  description = "Prefix inside the bucket."
  type        = string
}

variable "enforce_output_location" {
  description = <<-EOT
    Whether the workgroup enforces its own ResultConfiguration.OutputLocation
    (and other client-supplied settings) for every query. When true, dbt-athena's
    CTAS materializations silently drop any external_location/s3_data_dir the
    model configures -- Hive tables fall back to {output_location}/tables/{query-id}/
    regardless (see docs/architecture/roadmap-next-steps.md). Default true
    preserves existing behavior for workgroups created before this variable
    existed (mdp-athena-dev); set false only for a workgroup dedicated to a
    single trusted internal consumer (e.g. dbt's own build workgroup), never for
    one exposed to ad-hoc/external query tools.
  EOT
  type        = bool
  default     = true
}

variable "tags" {
  description = "Resource tags."

  type = map(string)

  default = {}
}