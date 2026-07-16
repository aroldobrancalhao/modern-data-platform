output "terraform_state_bucket_name" {
  description = "Terraform state bucket name."

  value = aws_s3_bucket.terraform_state.bucket
}

output "terraform_state_bucket_arn" {
  description = "Terraform state bucket ARN."

  value = aws_s3_bucket.terraform_state.arn
}