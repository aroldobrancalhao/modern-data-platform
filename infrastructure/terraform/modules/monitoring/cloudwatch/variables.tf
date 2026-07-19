variable "log_group_name" {
  description = "CloudWatch Log Group name."
  type        = string
}

variable "retention_in_days" {
  description = "Retention period in days."
  type        = number

  default = 30
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)

  default = {}
}