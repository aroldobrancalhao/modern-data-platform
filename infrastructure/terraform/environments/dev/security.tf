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

##########################################################
# BI Reader Policy Document
##########################################################
#
# Read-only identity for external BI tools that query Gold over
# Athena: Metabase (containerized, this compose) and Power BI
# (external, local/gateway). Neither can assume an IAM role natively
# without extra plumbing (Metabase's Athena driver and the Athena ODBC
# driver both authenticate with a static access key or the default
# credential chain, not sts:AssumeRole) -- an IAM User + long-lived
# access key is the standard shape for this kind of external,
# non-AWS-compute consumer, same reasoning as any BI/analytics client
# outside the account. Scope is deliberately narrow: only the Gold
# database/tables in Glue, only the `gold/` and `athena/` (query
# staging) prefixes in the data lake bucket, only the one Athena
# workgroup -- no access to bronze/, silver/, or any other Glue
# database.

data "aws_iam_policy_document" "bi_reader" {

  statement {

    sid = "AthenaQuery"

    effect = "Allow"

    actions = [
      "athena:StartQueryExecution",
      "athena:StopQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:GetQueryResultsStream",
      "athena:ListQueryExecutions",
      "athena:GetWorkGroup"
    ]

    resources = [
      module.athena.workgroup_arn
    ]
  }

  statement {

    sid = "AthenaListDataCatalogs"

    effect = "Allow"

    actions = [
      "athena:ListDataCatalogs"
    ]

    # Found live: the Metabase Athena driver's metadata-sync step
    # calls this before listing tables. Account-wide enumeration
    # action (no ARN it can be scoped to, per AWS's own Athena action
    # reference -- "Resource: *" is the only valid form) -- returns
    # only data catalog *names* (e.g. "AwsDataCatalog"), no schema/
    # table/data content, so unconditioned here isn't a least-
    # privilege compromise the way an unconditioned S3 grant would be.
    resources = ["*"]
  }

  statement {

    sid = "AthenaListDatabasesAndTables"

    effect = "Allow"

    actions = [
      # Found live: Metabase's Athena driver metadata-sync step calls
      # Athena's own ListDatabases/GetDatabase/*TableMetadata (Athena
      # API, distinct from the Glue Data Catalog Get* actions below --
      # both exist against the same underlying catalog, Athena's own
      # API layer requires its own grants). Scoped to the one data
      # catalog this project uses (AwsDataCatalog, confirmed via
      # athena:ListDataCatalogs above), not "*" -- these actions
      # support a datacatalog-level ARN per AWS's Athena action
      # reference.
      "athena:ListDatabases",
      "athena:GetDatabase",
      "athena:ListTableMetadata",
      "athena:GetTableMetadata"
    ]

    resources = [
      "arn:aws:athena:${var.aws_region}:${var.account_id}:datacatalog/AwsDataCatalog"
    ]
  }

  statement {

    sid = "GlueCatalogReadGold"

    effect = "Allow"

    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:BatchGetPartition"
    ]

    resources = [
      "arn:aws:glue:${var.aws_region}:${var.account_id}:catalog",
      "arn:aws:glue:${var.aws_region}:${var.account_id}:database/${module.glue_gold.database_name}",
      "arn:aws:glue:${var.aws_region}:${var.account_id}:table/${module.glue_gold.database_name}/*"
    ]
  }

  statement {

    sid = "S3ListGold"

    effect = "Allow"

    actions = [
      "s3:ListBucket"
    ]

    resources = [
      module.datalake.bucket_arn
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      # Reverted to gold/* only: the "" / "athena/*" values added
      # earlier didn't fix the HeadBucket/GetBucketLocation issue
      # (those calls carry no s3:prefix in their request context at
      # all -- a condition can't match a key that isn't present,
      # regardless of listed values) and staging moved to its own
      # dedicated bucket (module.athena_staging) instead, so there's
      # no longer any reason to reference athena/* here.
      values = ["gold/*"]
    }
  }

  statement {

    sid = "S3ReadGold"

    effect = "Allow"

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${module.datalake.bucket_arn}/gold/*"
    ]
  }

  statement {

    sid = "AthenaStagingBucketMetadata"

    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]

    resources = [
      module.athena_staging.bucket_arn
    ]

    # Unconditioned, unlike the main datalake bucket's ListGold
    # statement above -- this bucket holds nothing but Athena query
    # staging data, so bucket-level access here isn't a broadening
    # beyond what the identity needs, it's the correct scope for a
    # single-purpose bucket. Satisfies the Athena JDBC driver's
    # HeadBucket/GetBucketLocation connection-test step, which sends
    # no s3:prefix and so can never satisfy a prefix condition (see
    # ListGold's comment).
  }

  statement {

    sid = "S3AthenaQueryStaging"

    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListMultipartUploadParts",
      "s3:AbortMultipartUpload"
    ]

    resources = [
      "${module.athena_staging.bucket_arn}/*"
    ]
  }
}

##########################################################
# BI Reader IAM User
##########################################################

module "bi_reader" {

  source = "../../modules/security/iam_user"

  user_name = "mdp-bi-reader-dev"

  policy_name = "mdp-bi-reader-policy-dev"

  description = "Read-only access to the Gold layer (Athena/Glue/S3) for external BI tools (Metabase, Power BI)."

  policy = data.aws_iam_policy_document.bi_reader.json

  tags = local.default_tags
}