variable "aws_region" {
  description = "AWS Region."
  type        = string
}

variable "project_name" {
  description = "Project short name."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "account_id" {
  description = "AWS Account ID."
  type        = string
}

variable "owner" {
  description = "Resource owner."
  type        = string
}

variable "repository" {
  description = "Repository name."
  type        = string
}

variable "databricks_uc_external_id" {
  description = "External ID for the Unity Catalog storage credential trust policy on mdp-databricks-uc-role-dev. Real value returned by `databricks storage-credentials create` for the mdp_datalake_dev_credential storage credential (metastore 45fa7a63-28f5-4a0a-ae4a-0bb80adc6b96)."
  type        = string
  default     = "2bee29b9-125c-490a-bb0a-f16cd83a856f"
}