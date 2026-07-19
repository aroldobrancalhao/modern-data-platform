module "datalake_policy"

data "aws_iam_policy_document" "databricks_assume_role"

module "databricks_role"

module "databricks_attachment"