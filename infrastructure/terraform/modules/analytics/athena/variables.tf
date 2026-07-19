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

variable "tags" {
  description = "Resource tags."

  type = map(string)

  default = {}
}