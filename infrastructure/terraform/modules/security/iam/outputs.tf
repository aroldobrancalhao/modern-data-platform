output "role_arn" {

  description = "IAM Role ARN."

  value = aws_iam_role.this.arn
}

output "role_name" {

  description = "IAM Role name."

  value = aws_iam_role.this.name
}

output "policy_arn" {

  description = "IAM Policy ARN."

  value = aws_iam_policy.this.arn
}

output "policy_name" {

  description = "IAM Policy name."

  value = aws_iam_policy.this.name
}

output "attachment_id" {

  description = "IAM Attachment ID."

  value = aws_iam_role_policy_attachment.this.id
}