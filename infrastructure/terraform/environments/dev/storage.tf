##########################################################
# Data Lake
##########################################################

module "datalake" {
  source = "../../modules/storage/datalake"

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

##########################################################
# Data Lake Policy Document
##########################################################

data "aws_iam_policy_document" "datalake" {

  statement {

    sid = "ListBucket"

    effect = "Allow"

    actions = [
      "s3:ListBucket"
    ]

    resources = [
      module.datalake.bucket_arn
    ]
  }

  statement {

    sid = "ObjectAccess"

    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]

    resources = [
      "${module.datalake.bucket_arn}/*"
    ]
  }
}