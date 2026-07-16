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

##########################################################
# IAM Policy Document
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

##########################################################
# Data Lake Policy
##########################################################

module "datalake_policy" {

  source = "../../modules/iam-policy"

  name = "mdp-datalake-policy-dev"

  description = "Access policy for the Data Lake."

  policy = data.aws_iam_policy_document.datalake.json

  tags = local.default_tags
}

##########################################################
# Databricks Assume Role
##########################################################

data "aws_iam_policy_document" "databricks_assume_role" {

  statement {

    effect = "Allow"

    principals {

      type = "AWS"

      identifiers = [
        "arn:aws:iam::${var.account_id}:root"
      ]
    }

    actions = [
      "sts:AssumeRole"
    ]
  }
}

##########################################################
# Databricks Role
##########################################################

module "databricks_role" {

  source = "../../modules/iam-role"

  name = "mdp-databricks-role-dev"

  assume_role_policy = data.aws_iam_policy_document.databricks_assume_role.json

  tags = local.default_tags
}

##########################################################
# Policy Attachment
##########################################################

module "databricks_attachment" {

  source = "../../modules/iam-attachment"

  role_name = module.databricks_role.name

  policy_arn = module.datalake_policy.arn
}