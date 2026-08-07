variable "user_name" {

  description = "IAM User name."

  type = string
}

variable "policy_name" {

  description = "IAM Policy name."

  type = string
}

variable "description" {

  description = "IAM Policy description."

  type = string
}

variable "policy" {

  description = "IAM Policy document."

  type = string
}

variable "tags" {

  description = "Resource tags."

  type = map(string)

  default = {}
}
