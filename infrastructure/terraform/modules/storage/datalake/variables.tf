variable "bucket_name" {
  description = "S3 bucket name."
  type        = string
}

variable "versioning_enabled" {
  description = "Enable bucket versioning."
  type        = bool
  default     = true
}

variable "prevent_destroy" {
  description = "Prevent bucket destruction."
  type        = bool
  default     = false
}

variable "force_destroy" {
  description = "Force bucket deletion."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
  default     = {}
}

variable "folders" {
  description = "List of folder prefixes to create inside the bucket."
  type        = list(string)
  default     = []
}