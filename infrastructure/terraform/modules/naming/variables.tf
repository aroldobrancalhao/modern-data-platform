variable "project_name" {
  description = "Project short name."
  type        = string
}

variable "resource_name" {
  description = "Resource logical name."
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