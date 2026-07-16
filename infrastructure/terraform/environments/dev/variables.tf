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