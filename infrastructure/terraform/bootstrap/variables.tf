variable "aws_region" {
  description = "AWS region where resources will be created."
  type        = string
}

variable "project_name" {
  description = "Project name."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
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

variable "terraform_state_bucket" {
  description = "Terraform remote state bucket name."
  type        = string
}