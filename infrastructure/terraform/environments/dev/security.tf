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
# Databricks IAM
##########################################################

module "databricks_iam" {

  source = "../../modules/security/iam"

  role_name = "mdp-databricks-role-dev"

  policy_name = "mdp-datalake-policy-dev"

  description = "Access policy for the Data Lake."

  assume_role_policy = data.aws_iam_policy_document.databricks_assume_role.json

  policy = data.aws_iam_policy_document.datalake.json

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

##########################################################
# Glue IAM
##########################################################

module "glue_iam" {

  source = "../../modules/security/iam"

  role_name = "mdp-glue-role-dev"

  policy_name = "mdp-glue-policy-dev"

  description = "Glue permissions."

  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json

  policy = data.aws_iam_policy_document.glue.json

  tags = local.default_tags
}