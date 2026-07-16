variable "database_name" {
  description = "Glue Database name."
  type        = string
}

variable "crawler_name" {
  description = "Glue Crawler name."
  type        = string
}

variable "crawler_role_arn" {
  description = "Glue IAM Role ARN."
  type        = string
}

variable "bucket_name" {
  description = "S3 bucket name."
  type        = string
}

variable "crawler_path" {
  description = "Crawler S3 prefix."
  type        = string
}

variable "tags" {
  description = "Resource tags."

  type = map(string)

  default = {}
}