module "naming" {
  source = "../../modules/naming"

  project_name  = var.project_name
  resource_name = "datalake"
  environment   = var.environment
  account_id    = var.account_id
}

module "datalake" {
  source = "../../modules/s3"

  bucket_name = module.naming.bucket_name

  versioning_enabled = true

  force_destroy = false

  tags = local.default_tags

  folders = [
    "bronze/",
    "silver/",
    "gold/",
    "checkpoints/",
    "schemas/",
    "athena/",
    "logs/",
    "tmp/"
  ]
}