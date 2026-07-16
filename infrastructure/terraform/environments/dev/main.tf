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

module "cloudwatch_airflow" {
  source = "../../modules/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/airflow"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_glue" {
  source = "../../modules/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/glue"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_databricks" {
  source = "../../modules/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/databricks"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_athena" {
  source = "../../modules/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/athena"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_platform" {
  source = "../../modules/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/platform"
  retention_in_days = 30

  tags = local.default_tags
}

module "cloudwatch_terraform" {
  source = "../../modules/cloudwatch"

  log_group_name    = "/${var.project_name}/${var.environment}/terraform"
  retention_in_days = 30

  tags = local.default_tags
}

##########################################################
# Glue Policy Document
##########################################################

data "aws_iam_policy_document" "glue" {

  statement {

    sid = "GlueDataLakeAccess"

    effect = "Allow"

    actions = [
      "s3:ListBucket"
    ]

    resources = [
      module.datalake.bucket_arn
    ]
  }

  statement {

    sid = "GlueObjects"

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

  statement {

    sid = "GlueCatalog"

    effect = "Allow"

    actions = [
      "glue:*"
    ]

    resources = [
      "*"
    ]
  }

  statement {

    sid = "CloudWatchLogs"

    effect = "Allow"

    actions = [
      "logs:*"
    ]

    resources = [
      "*"
    ]
  }
}

module "glue_policy" {

  source = "../../modules/iam-policy"

  name = "mdp-glue-policy-dev"

  description = "Glue permissions."

  policy = data.aws_iam_policy_document.glue.json

  tags = local.default_tags
}

##########################################################
# Glue Assume Role
##########################################################

data "aws_iam_policy_document" "glue_assume_role" {

  statement {

    effect = "Allow"

    principals {

      type = "Service"

      identifiers = [
        "glue.amazonaws.com"
      ]
    }

    actions = [
      "sts:AssumeRole"
    ]
  }
}

module "glue_role" {

  source = "../../modules/iam-role"

  name = "mdp-glue-role-dev"

  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json

  tags = local.default_tags
}

module "glue_attachment" {

  source = "../../modules/iam-attachment"

  role_name = module.glue_role.name

  policy_arn = module.glue_policy.arn
}

module "glue_bronze" {

  source = "../../modules/glue"

  database_name = "mdp_bronze_dev"

  crawler_name = "mdp-bronze-crawler-dev"

  crawler_role_arn = module.glue_role.arn

  bucket_name = module.datalake.bucket_name

  crawler_path = "bronze/"

  tags = local.default_tags
}

module "glue_silver" {

  source = "../../modules/glue"

  database_name = "mdp_silver_dev"

  crawler_name = "mdp-silver-crawler-dev"

  crawler_role_arn = module.glue_role.arn

  bucket_name = module.datalake.bucket_name

  crawler_path = "silver/"

  tags = local.default_tags
}

module "glue_gold" {

  source = "../../modules/glue"

  database_name = "mdp_gold_dev"

  crawler_name = "mdp-gold-crawler-dev"

  crawler_role_arn = module.glue_role.arn

  bucket_name = module.datalake.bucket_name

  crawler_path = "gold/"

  tags = local.default_tags
}

