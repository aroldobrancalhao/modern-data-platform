resource "aws_glue_catalog_database" "this" {

  name = var.database_name

}

resource "aws_glue_crawler" "this" {

  name = var.crawler_name

  role = var.crawler_role_arn

  database_name = aws_glue_catalog_database.this.name

  s3_target {

    path = "s3://${var.bucket_name}/${var.crawler_path}"

  }

  schema_change_policy {

    delete_behavior = "LOG"

    update_behavior = "UPDATE_IN_DATABASE"

  }

  tags = var.tags
}