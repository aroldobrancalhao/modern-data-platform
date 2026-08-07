output "user_name" {

  description = "IAM User name."

  value = aws_iam_user.this.name
}

output "user_arn" {

  description = "IAM User ARN."

  value = aws_iam_user.this.arn
}

output "policy_arn" {

  description = "IAM Policy ARN."

  value = aws_iam_policy.this.arn
}

output "policy_name" {

  description = "IAM Policy name."

  value = aws_iam_policy.this.name
}

output "access_key_id" {

  description = "IAM Access Key ID."

  value = aws_iam_access_key.this.id
}

output "secret_access_key" {

  description = "IAM Secret Access Key."

  value = aws_iam_access_key.this.secret

  sensitive = true
}
