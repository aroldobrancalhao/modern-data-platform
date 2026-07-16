output "arn" {

  description = "CloudWatch Log Group ARN."

  value = aws_cloudwatch_log_group.this.arn
}

output "name" {

  description = "CloudWatch Log Group name."

  value = aws_cloudwatch_log_group.this.name
}