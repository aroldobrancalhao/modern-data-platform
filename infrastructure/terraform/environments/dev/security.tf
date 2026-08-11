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

  role_name = module.naming_databricks_role.resource_prefix

  policy_name = module.naming_datalake_policy.resource_prefix

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
# The ARN is built from var.account_id + the role name (via
# module.naming_databricks_uc_role -- a plain string-formatting
# module, not the role resource itself, so this carries no circular
# dependency) rather than referencing aws_iam_role.databricks_uc.arn
# directly, since this document is itself the role's
# assume_role_policy -- referencing the role's own attribute here
# would be circular.
data "aws_iam_policy_document" "databricks_uc_assume_role" {

  statement {

    effect = "Allow"

    principals {

      type = "AWS"

      identifiers = [
        "arn:aws:iam::414351767826:role/unity-catalog-prod-UCMasterRole-14S5ZJVKOTYTL",
        "arn:aws:iam::${var.account_id}:role/${module.naming_databricks_uc_role.resource_prefix}"
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

  name = module.naming_databricks_uc_role.resource_prefix

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

  role_name = module.naming_glue_role.resource_prefix

  policy_name = module.naming_glue_policy.resource_prefix

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

  user_name = module.naming_bi_reader.resource_prefix

  policy_name = module.naming_bi_reader_policy.resource_prefix

  description = "Read-only access to the Gold layer (Athena/Glue/S3) for external BI tools (Metabase, Power BI)."

  policy = data.aws_iam_policy_document.bi_reader.json

  tags = local.default_tags
}

##########################################################
# Airflow Ingest IAM Policy
##########################################################
#
# Scoped to exactly what Airflow's own AWS credential does today, read
# from the real code, not assumed (roadmap-next-steps.md): the
# `extract_postgres` task (raw/ read+write+list+delete via
# PostgresExtractionStage/S3StorageProvider) and remote task-log
# shipping to the CloudWatch log group Terraform already provisions
# (module.cloudwatch_airflow, monitoring.tf), via the `aws_default`
# Connection every Airflow container uses for
# AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID.
#
# Deliberately does NOT cover the `dbt_run_gold`/`dbt_test_gold`
# BashOperator tasks (Athena `mdp-athena-dbt-dev` workgroup, Glue
# read on mdp_silver_dev, Glue write on mdp_gold_dev, S3 read on
# silver/ + write on gold/) -- confirmed live that this DAG's dbt
# steps need real write access to build Gold, which would have made
# this identity nearly as broad as the personal key it's replacing.
# Left on the personal credential for now (a deliberate, narrower-
# scope decision, not an oversight) -- see
# marketplace_batch_pipeline.py's BashOperator env overrides for how
# the split is wired, and roadmap-next-steps.md for the remaining-work
# entry this leaves behind.
data "aws_iam_policy_document" "airflow_ingest" {

  statement {

    sid = "S3ListRaw"

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
      values   = ["raw/*"]
    }
  }

  statement {

    sid = "S3ReadWriteRaw"

    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]

    resources = [
      "${module.datalake.bucket_arn}/raw/*"
    ]
  }

  statement {

    sid = "CloudWatchAirflowLogs"

    effect = "Allow"

    actions = [
      # CreateLogGroup: found live -- Airflow's CloudWatch log handler
      # (watchtower) calls this defensively before creating a log
      # stream, even though the group already exists (Terraform-
      # managed, module.cloudwatch_airflow). IAM evaluates the action
      # grant before the "already exists" business logic runs, so
      # omitting it (assumed unnecessary since the group pre-exists)
      # denied the call outright and crash-looped the dag-processor
      # job entirely, not just remote logging -- confirmed via
      # dag-processor container logs, not assumed.
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
      "logs:GetLogEvents"
    ]

    resources = [
      module.cloudwatch_airflow.arn,
      "${module.cloudwatch_airflow.arn}:*"
    ]
  }

  statement {

    sid = "CloudWatchPlatformLogs"

    effect = "Allow"

    actions = [
      # Same 5 actions as CloudWatchAirflowLogs above, same reason:
      # watchtower.CloudWatchLogHandler calls CreateLogGroup
      # defensively regardless of the group already existing --
      # confirmed live with the Airflow handler (see that statement's
      # own comment), reused here rather than re-discovering it.
      # This identity's own AWS_ACCESS_KEY_ID/SECRET (the generic
      # boto3-default names in infrastructure/docker/.env) is what
      # scripts/run_postgres_extraction_once.py,
      # scripts/run_silver_catalog_registration_once.py and
      # airflow/config/bootstrap.py run under inside the Airflow
      # containers -- the three non-DAG-task callers of
      # configure_logging() that can now ship to the platform log
      # group (module.cloudwatch_platform, monitoring.tf).
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
      "logs:GetLogEvents"
    ]

    resources = [
      module.cloudwatch_platform.arn,
      "${module.cloudwatch_platform.arn}:*"
    ]
  }

  statement {

    sid = "CloudWatchDatabricksLogs"

    effect = "Allow"

    actions = [
      # Deliberately narrower than CloudWatchAirflowLogs/
      # CloudWatchPlatformLogs above: no CreateLogGroup (the group is
      # Terraform-provisioned, module.cloudwatch_databricks, and
      # integrations/databricks/observability/run_output_shipper.py
      # passes create_log_group=False -- watchtower's own source only
      # calls CreateLogGroup when that flag is true, confirmed by
      # reading it, so this action is never exercised here and isn't
      # granted). No DescribeLogStreams/GetLogEvents either --
      # watchtower's write path never calls either (confirmed the same
      # way); those two were only ever useful for an operator manually
      # reading logs back with the AWS CLI, which uses a different
      # credential (the personal terraform-admin key), not this
      # identity. Least-privilege scoped to exactly what the code path
      # exercises: CreateLogStream (idempotent, watchtower calls it
      # once per stream) and PutLogEvents.
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      module.cloudwatch_databricks.arn,
      "${module.cloudwatch_databricks.arn}:*"
    ]
  }
}

##########################################################
# Airflow Ingest IAM User
##########################################################

module "airflow_ingest" {

  source = "../../modules/security/iam_user"

  user_name = module.naming_airflow_ingest.resource_prefix

  policy_name = module.naming_airflow_ingest_policy.resource_prefix

  description = "Scoped access for Airflow's own AWS credential: raw/ S3 read-write (extract_postgres) and the Airflow CloudWatch log group (remote task logging). Does not cover dbt_run_gold/dbt_test_gold, which stay on the personal key -- see roadmap-next-steps.md."

  policy = data.aws_iam_policy_document.airflow_ingest.json

  tags = local.default_tags
}

##########################################################
# Bronze Consumer IAM User
##########################################################

# Scope confirmed by reading src/streaming/consumers/bronze_consumer.py
# and its call graph directly, not assumed from the entity's name:
# the only AWS-touching call in the whole module is
# write_deltalake(StorageConfig.bronze(entity), table, mode="append")
# -- append-only writes to s3://.../bronze/{entity}/, one Delta table
# per streaming entity, never read back by this process. No Silver/
# Gold/Athena/Glue call anywhere in this module -- it doesn't join or
# query analytically, it just lands CDC events (see the module's own
# docstring). resolve_bronze_schema() (data_platform.compute.
# bronze_schema) queries Postgres information_schema.columns directly
# via psycopg -- a Postgres credential concern (POSTGRES_USER/
# PASSWORD, already in docker-compose.yml), not AWS IAM, so it isn't
# part of this policy.
data "aws_iam_policy_document" "bronze_consumer" {

  statement {

    sid = "S3ListBronze"

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
      values   = ["bronze/*"]
    }
  }

  statement {

    sid = "S3ReadWriteBronze"

    effect = "Allow"

    actions = [
      # No s3:DeleteObject, deliberately, unlike airflow_ingest's
      # raw/* grant -- bronze_consumer.py only ever calls
      # write_deltalake(..., mode="append"), append-only per this
      # module's own docstring ("Bronze keeps every version of a row
      # it has ever seen"). It never deletes, compacts or vacuums its
      # own table (that's optimize_bronze.ipynb, a separate batch-flow
      # process against a *different* physical table --
      # StorageConfig.bronze_batch(), not .bronze() -- see
      # roadmap-next-steps.md's Bronze batch/streaming-split entry).
      # GetObject is still needed even for a pure-append writer: every
      # write_deltalake() call reads the current _delta_log first to
      # determine the next commit version.
      "s3:GetObject",
      "s3:PutObject"
    ]

    resources = [
      "${module.datalake.bucket_arn}/bronze/*"
    ]
  }

  statement {

    sid = "CloudWatchPlatformLogs"

    effect = "Allow"

    actions = [
      # Same 5 actions/reasoning as airflow_ingest's own
      # CloudWatchPlatformLogs statement above -- this identity's
      # AWS_ACCESS_KEY_ID/SECRET (MDP_BRONZE_CONSUMER_*) is what
      # scripts/run_bronze_consumer.py runs under, the fourth (and
      # only long-running) configure_logging() caller.
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
      "logs:GetLogEvents"
    ]

    resources = [
      module.cloudwatch_platform.arn,
      "${module.cloudwatch_platform.arn}:*"
    ]
  }
}

module "bronze_consumer" {

  source = "../../modules/security/iam_user"

  user_name = module.naming_bronze_consumer.resource_prefix

  policy_name = module.naming_bronze_consumer_policy.resource_prefix

  description = "Scoped access for the Bronze Consumer's own AWS credential: bronze/ S3 read-write only (append-only Delta writes). Currently shares Airflow's personal-key fallback (MDP_PERSONAL_ACCESS_KEY_ID/SECRET) in infrastructure/docker/docker-compose.yml -- see roadmap-next-steps.md."

  policy = data.aws_iam_policy_document.bronze_consumer.json

  tags = local.default_tags
}

##########################################################
# dbt (Gold build) IAM User
##########################################################
#
# Closes the "remaining work" item named in airflow_ingest's own
# policy-document comment above: dbt_run_gold/dbt_test_gold
# (marketplace_batch_pipeline.py's BashOperator, env-overridden onto
# MDP_PERSONAL_ACCESS_KEY_ID/SECRET, see that DAG) are still on the
# personal terraform-admin key. Scope mirrors that comment exactly --
# Athena mdp-athena-dbt-dev, Glue read mdp_silver_dev / write
# mdp_gold_dev, S3 read silver/ / write gold/ -- derived from what
# `dbt run --target dbt_build --select gold` + `dbt test` actually do
# (dbt/models/gold/*.sql ref() the stg_* Silver models directly, and
# CTAS-builds/replaces the Gold tables), not assumed.
data "aws_iam_policy_document" "dbt_gold" {

  statement {

    sid = "AthenaDbtBuild"

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
      module.athena_dbt_build.workgroup_arn
    ]
  }

  statement {

    sid = "AthenaListDataCatalogs"

    effect = "Allow"

    actions = [
      "athena:ListDataCatalogs"
    ]

    # Same as bi_reader's identical statement -- account-wide
    # enumeration action, no ARN it can be scoped to (per AWS's own
    # Athena action reference), returns only data catalog *names*.
    resources = ["*"]
  }

  statement {

    sid = "AthenaListDatabasesAndTables"

    effect = "Allow"

    actions = [
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

    sid = "GlueCatalogReadSilver"

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
      "arn:aws:glue:${var.aws_region}:${var.account_id}:database/${module.glue_silver.database_name}",
      "arn:aws:glue:${var.aws_region}:${var.account_id}:table/${module.glue_silver.database_name}/*"
    ]
  }

  statement {

    sid = "GlueCatalogWriteGold"

    effect = "Allow"

    actions = [
      # Read side (needed even for a writer -- dbt's adapter checks
      # existing table/schema state before CTAS-replacing it) plus the
      # DDL/partition-management actions dbt-athena's create_table_as
      # macro and --full-refresh's drop+recreate path actually issue.
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:DeleteTable",
      "glue:GetPartition",
      "glue:GetPartitions",
      "glue:BatchGetPartition",
      "glue:BatchCreatePartition",
      "glue:BatchDeletePartition"
    ]

    resources = [
      "arn:aws:glue:${var.aws_region}:${var.account_id}:catalog",
      "arn:aws:glue:${var.aws_region}:${var.account_id}:database/${module.glue_gold.database_name}",
      "arn:aws:glue:${var.aws_region}:${var.account_id}:table/${module.glue_gold.database_name}/*"
    ]
  }

  statement {

    sid = "S3ListSilverAndGold"

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
      values   = ["silver/*", "gold/*"]
    }
  }

  statement {

    sid = "S3ReadSilver"

    effect = "Allow"

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${module.datalake.bucket_arn}/silver/*"
    ]
  }

  statement {

    sid = "S3ReadWriteGold"

    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      # Unlike bronze_consumer's append-only grant, DeleteObject is
      # real here: --full-refresh's drop+recreate (see the Gold
      # CTAS-location roadmap entry, "a rebuild genuinely overwrites
      # in place again") needs to clear old data files under a Gold
      # table's location before/while writing the replacement.
      "s3:DeleteObject"
    ]

    resources = [
      "${module.datalake.bucket_arn}/gold/*"
    ]
  }

  statement {

    sid = "AthenaDbtStagingBucketMetadata"

    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]

    resources = [
      module.athena_staging.bucket_arn
    ]

    # Bucket-level, unconditioned, same reasoning as bi_reader's
    # identical statement -- the Athena JDBC/ODBC connection-test path
    # (HeadBucket/GetBucketLocation) carries no s3:prefix, so a prefix
    # condition can never match it.
  }

  statement {

    sid = "S3AthenaDbtQueryStaging"

    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListMultipartUploadParts",
      "s3:AbortMultipartUpload"
    ]

    # Scoped to dbt-build/* specifically, not the whole staging
    # bucket like bi_reader's equivalent grant -- module.athena_dbt_build
    # sets results_prefix = "dbt-build/" (analytics.tf), a dedicated
    # sub-path within the shared staging bucket, unlike mdp-athena-dev's
    # results_prefix = "" (bucket root) that bi_reader legitimately
    # needs full-bucket access for.
    resources = [
      "${module.athena_staging.bucket_arn}/dbt-build/*"
    ]
  }
}

module "dbt_gold" {

  source = "../../modules/security/iam_user"

  user_name = module.naming_dbt_gold.resource_prefix

  policy_name = module.naming_dbt_gold_policy.resource_prefix

  description = "Scoped access for dbt's own AWS credential (dbt_run_gold/dbt_test_gold): mdp-athena-dbt-dev workgroup, Glue read on mdp_silver_dev, Glue write on mdp_gold_dev, S3 read silver/ + read-write gold/. Wired into airflow/dags/marketplace_batch_pipeline.py's DBT_AWS_CREDENTIALS -- replaces MDP_PERSONAL_ACCESS_KEY_ID/SECRET for those two tasks, see roadmap-next-steps.md."

  policy = data.aws_iam_policy_document.dbt_gold.json

  tags = local.default_tags
}