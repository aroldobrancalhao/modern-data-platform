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
# Databricks Unity Catalog Assume Role
##########################################################
#
# Dedicated role for a Unity Catalog Storage Credential (External
# Location), separate from mdp-databricks-role-dev above -- that
# role's trust policy trusts this AWS account's own root, which is
# not how Unity Catalog assumes a role (it assumes it from a fixed
# Databricks-owned role in Databricks' own AWS account). See
# docs/architecture/roadmap-next-steps.md for the investigation.
#
# The trust below is the officially documented Databricks pattern:
# trust the fixed "UC Master Role" ARN (constant across every
# Databricks account on commercial AWS) with an ExternalId condition.
# Databricks only tells us the real ExternalId after the storage
# credential is created referencing this role's ARN -- until then,
# var.databricks_uc_external_id stays at the documented placeholder
# ("0000"). This is a circular dependency by design (Databricks'
# own docs use the same placeholder-then-update flow), not a
# temporary workaround of our own invention.
#
# Also trusts the role's own ARN: Unity Catalog requires this role to
# be able to assume itself (confirmed by `databricks
# storage-credentials validate`: "non self-assuming"). The identity
# side of that (aws_iam_role_policy.databricks_uc_self_assume,
# granting sts:AssumeRole on this same ARN) isn't enough on its own --
# the trust policy also has to allow the role itself as a principal.
# The ARN is built from var.account_id + the literal role name rather
# than referencing aws_iam_role.databricks_uc.arn, since this document
# is itself the role's assume_role_policy -- referencing the role's
# own attribute here would be a circular dependency.
data "aws_iam_policy_document" "databricks_uc_assume_role" {

  statement {

    effect = "Allow"

    principals {

      type = "AWS"

      identifiers = [
        "arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL",
        "arn:aws:iam::${var.account_id}:role/mdp-databricks-uc-role-dev"
      ]
    }

    actions = [
      "sts:AssumeRole"
    ]

    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [var.databricks_uc_external_id]
    }
  }
}

##########################################################
# Databricks Unity Catalog IAM Role
##########################################################
#
# Reuses the existing mdp-datalake-policy-dev policy
# (module.databricks_iam.policy_arn, backed by
# data.aws_iam_policy_document.datalake in storage.tf) instead of
# declaring a second copy of the same S3 permissions -- same policy
# object, attached to two roles.

resource "aws_iam_role" "databricks_uc" {

  name = "mdp-databricks-uc-role-dev"

  description = "Assumed by Databricks Unity Catalog to access the Data Lake bucket via a Storage Credential / External Location."

  assume_role_policy = data.aws_iam_policy_document.databricks_uc_assume_role.json

  tags = local.default_tags
}

resource "aws_iam_role_policy_attachment" "databricks_uc" {

  role = aws_iam_role.databricks_uc.name

  policy_arn = module.databricks_iam.policy_arn
}

# Unity Catalog requires this role to be able to assume itself
# (confirmed by `databricks storage-credentials validate`: "The IAM
# role for this storage credential was found to be non self-assuming"
# -- documented Databricks requirement, not specific to our bucket
# permissions, so it's a separate inline policy rather than another
# statement in the shared mdp-datalake-policy-dev).
resource "aws_iam_role_policy" "databricks_uc_self_assume" {

  name = "self-assume"

  role = aws_iam_role.databricks_uc.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = aws_iam_role.databricks_uc.arn
      }
    ]
  })
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