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
# Athena Staging Bucket
##########################################################
#
# Dedicated bucket for Athena query results/staging, separate from the
# main datalake bucket (bronze/silver/gold/checkpoints). Found live:
# the Athena JDBC driver (Metabase's connection-test step) calls
# HeadBucket/GetBucketLocation on the output-location bucket before
# ever running a query -- neither call carries an s3:prefix in its
# request context, so a prefix-conditioned IAM policy (what the BI
# Reader had on the shared datalake bucket's `athena/` prefix) can
# never satisfy them, regardless of which prefix values are listed.
# Fixing this by granting unconditioned s3:ListBucket on the *shared*
# datalake bucket would leak bronze/silver/gold/checkpoints key names
# to a read-only BI identity that has no business seeing them -- more
# access than necessary. A single-purpose bucket sidesteps that
# entirely: unconditioned bucket-level access here isn't a broadening,
# it's the correct scope for a bucket that holds nothing but Athena
# staging data in the first place.

module "athena_staging" {
  source = "../../modules/storage/datalake"

  bucket_name = module.naming_athena_staging.bucket_name

  versioning_enabled = false

  force_destroy = true

  tags = local.default_tags

  folders = []
}

##########################################################
# Data Lake Policy Document
##########################################################

data "aws_iam_policy_document" "datalake" {

  statement {

    sid = "ListBucket"

    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:ListBucketMultipartUploads"
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
      "s3:DeleteObject",
      "s3:ListMultipartUploadParts",
      "s3:AbortMultipartUpload"
    ]

    resources = [
      "${module.datalake.bucket_arn}/*"
    ]
  }
}