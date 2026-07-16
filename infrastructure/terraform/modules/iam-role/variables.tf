variable "name" {
  description = "IAM Role name."
  type        = string
}

variable "assume_role_policy" {
  description = "IAM Assume Role Policy."
  type        = string
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)

  default = {}
}