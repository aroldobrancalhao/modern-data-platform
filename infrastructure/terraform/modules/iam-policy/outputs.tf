output "arn" {
  description = "IAM Policy ARN."

  value = aws_iam_policy.this.arn
}

output "name" {
  description = "IAM Policy name."

  value = aws_iam_policy.this.name
}