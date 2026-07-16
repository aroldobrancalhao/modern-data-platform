resource "aws_athena_workgroup" "this" {

  name = var.workgroup_name

  configuration {

    enforce_workgroup_configuration = true

    publish_cloudwatch_metrics_enabled = true

    result_configuration {

      output_location = "s3://${var.results_bucket}/${var.results_prefix}"

      encryption_configuration {

        encryption_option = "SSE_S3"

      }
    }
  }

  tags = var.tags
}